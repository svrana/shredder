import copy
from multiprocessing import Pipe, Process, JoinableQueue
import logging
import os
import signal
from time import sleep
import sys


class WorkerContext(object):
    """ Holds all info associated with a Worker process. Used by the master
    process to handle state belonging to each of its workers.
    """
    def __init__(self, name, process, pipe):
        self.name = name
        self.process = process
        self.pipe = pipe
        self.pid = process.pid

    def close(self):
        if self.pipe:
            self.pipe.close()
            self.pipe = None

        if self.process:
            self.process.join()
            self.process = None

    def send_shutdown(self):
        self.pipe.send(dict(shutdown='hard'))
        os.kill(self.pid, signal.SIGUSR1)

    def read(self):
        msgs = []

        while self.pipe.poll():
            msg = self.pipe.recv()
            msgs.append(msg)

        return msgs


class Workers(object):
    """ Holds on to all WorkerContexts and facilitates iteracting with each
    process. """
    def __init__(self):
        self.workers = []

    def add(self, worker):
        self.workers.append(worker)

    def cleanup(self):
        for worker in self.workers:
            worker.close()

        self.workers = []

    def shutdown(self):
        for worker in self.workers:
            worker.send_shutdown()

        sleep(.1) # give workers time to read pipe
        self.cleanup()

    def send_poison_pill(self, queue):
        for _ in self.workers:
            queue.put(None)

    def read(self):
        all_msgs = []

        for worker in self.workers:
            msg_list = worker.read()
            for msg in msg_list:
                all_msgs.append(msg)

        return all_msgs


class Worker(object):
    """ This is the state of the worker from the point of view of the worker
    process. It receives data from the queue and feeds it to the function
    provided. """
    def __init__(self, name, queue, pipe, work_fn):
        self.logger = logging.getLogger('shredder.worker')
        self.name = 'worker-%d' % name
        self.queue = queue
        self.pipe = pipe
        self.work_fn = work_fn

    @classmethod
    def start(cls, name, queue, pipe, work_fn):
        worker = cls(name, queue, pipe, work_fn)

        signal.signal(signal.SIGUSR1, worker.signal_handler)

        worker.run()

    def dispatch_cmd(self, command, value):
        if command == 'shutdown':
            self.quit()
        else:
            self.logger.warn("unknown command: %s with value: %s", command, value)

    def read_incoming_cmd(self):
        got_msg = False

        while self.pipe.poll():
            msg_dict = self.pipe.recv()
            got_msg = True
            for k,v in msg_dict.iteritems():
                self.dispatch_cmd(k, v)

        if got_msg is False:
            self.logger.warn("%s expected a message", self.name)

    def quit(self):
        self.logger.debug('%s quitting', self.name)
        self.stop()
        sys.stdout.flush()
        sys.exit(0)

    def signal_handler(self, signum, stack_handler):
        if signum == signal.SIGUSR1:
            self.logger.debug("%s got sigusr1", self.name)
            self.read_incoming_cmd()

    def stop(self):
        self.logger.debug("%s stopping", self.name)
        self.pipe.close()

    def do_work(self, work):
        data = self.work_fn(work)
        self.pipe.send(data)

    def run(self):
        self.logger.debug("%s ready", self.name)

        while True:
            try:
                work = self.queue.get()
            except (KeyboardInterrupt, SystemExit):
                break
            if work is None:
                self.logger.debug("%s finished its work, shutting down", self.name)
                self.queue.task_done()
                self.quit()
            else:
                self.do_work(work)
                self.queue.task_done()


class Shredder(object):
    def __init__(self, work_generator, work_fn, aggregator, num_processes):
        logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger('shredder')
        self.work_generator = work_generator
        self.work_fn = work_fn
        self.aggregator = aggregator
        self.num_processes = num_processes
        self.queue = JoinableQueue()
        self.workers = Workers()

    def signal_handler(self, signum, stack_handler):
        self.logger.info("shutting down")
        signal.setitimer(signal.ITIMER_REAL, 0, 0) # clear
        self.workers.shutdown()
        sys.exit(0)

    def aggregate_results(self, signum, stack_handler):
        msgs = self.workers.read()
        for msg in msgs:
            self.aggregator(msg)

    def launch_workers(self):
        for i in range(0, self.num_processes):
            self.logger.info("launching worker-%d", i)
            worker = self.launch(i)
            self.workers.add(worker)

    def shred(self):
        for chunk in self.work_generator():
            if chunk is None:
                self.logger.warn("Got None from generator...ignoring")
                continue

            self.queue.put(copy.deepcopy(chunk))

            while self.queue.qsize() > self.num_processes:
                sleep(5)

    def start(self):
        self.launch_workers()

        signal.signal(signal.SIGINT, self.signal_handler)

        signal.signal(signal.SIGALRM, self.aggregate_results)
        signal.setitimer(signal.ITIMER_REAL, 5, 5)

        self.shred()

        self.logger.info("Shredded; workers will shutdown when queue empties")

        self.workers.send_poison_pill(self.queue)
        self.queue.join()
        self.workers.cleanup()

        self.logger.info("Done")

    def launch(self, name):
        """ Start a new Worker process that will consume work from the queue.
        """
        parent_pipe, child_pipe = Pipe()

        process = Process(target=Worker.start,
                          args=(name, self.queue, child_pipe, self.work_fn))
        process.start()

        worker = WorkerContext(name, process, parent_pipe)
        return worker
