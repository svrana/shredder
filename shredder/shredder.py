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
        self.pipe.close()
        self.process.join()

    def send_shutdown(self, shutdown_type):
        #if shutdown_type == 'soft':
        #    self.pipe.send(dict(shutdown=shutdown_type))
        #else:
        os.kill(self.pid, signal.SIGINT)

class Worker(object):
    def __init__(self, name, queue, pipe, work_fn):
        self.logger = logging.getLogger('shredder.worker')
        self.name = name
        self.queue = queue
        self.pipe = pipe
        self.work_fn = work_fn

    @classmethod
    def start(cls, name, queue, pipe, work_fn):

        worker = cls(name, queue, pipe, work_fn)

        signal.signal(signal.SIGINT, worker.signal_handler)

        worker.run()

    def signal_handler(self, signum, stack_handler):
        self.stop()
        sys.exit(0)

    def stop(self):
        self.logger.info("worker%d stopping", self.name)
        self.pipe.close()

    def do_work(self, work):
        data = self.work_fn(work)
        self.pipe.send(dict(result=data))

    def run(self):
        self.logger.info("worker%d ready", self.name)

        while True:
            work = self.queue.get()
            self.do_work(work)
            self.queue.task_done()

class Shredder(object):
    def __init__(self, work_generator, work_fn, aggregator, num_processes):
        logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger('shredder')
        self.work_generator = work_generator
        self.work_fn = work_fn
        self.num_processes = num_processes
        self.queue = JoinableQueue()
        self.workers = {}

    def shutdown_workers(self, shutdown_type):
        for context in self.workers.itervalues():
            context.send_shutdown(shutdown_type)
            context.close()

        self.queue.join()

    def soft_kill(self):
        self.logger.info("interrupt received..")
        self.shutdown_workers('hard')

    def start(self):
        #signal.signal(signal.SIGINT, self.soft_kill)
        #signal.signal(signal.SIGTERM, signal.SIG_DFL)
        for i in range(0, self.num_processes):
            self.logger.info("launching worker%d", i)
            self.launch(i)

#        import pdb
#        pdb.set_trace()
#
#        for chunk in self.work_generator():
#            self.queue.put(copy.deepcopy(chunk))
#
#            while self.queue.qsize() > 1:
#                sleep(5)

        self.logger.info("Data shredded..")

        self.shutdown_workers('soft')

        self.logger.info("Done")

    def launch(self, name):
        """ Start a new Worker process that will consume work from the queue. """
        parent_pipe, child_pipe = Pipe()

        process = Process(target=Worker.start,
                          args=(name, self.queue, child_pipe, self.work_fn))
        process.start()

        self.workers[name] = WorkerContext(name, process, parent_pipe)
