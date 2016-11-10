shredder
==========

An easy way to distribute work to processes and aggregate results.

Installation
------------

To install shredder:

.. code-block:: bash

    $ sudo pip install shredder

or from source:

.. code-block:: bash

    $ sudo python setup.py install


Getting Started
---------------


.. code-block:: pycon

    >>> from shredder import Shredder
    >>>
    >>>
    >>> function work_generator:
    >>>     with open(f) as f:
    >>>         yield readline(f)
    >>>
    >>> function worker(shredder, data):
    >>>    results = do_something_with_data(data)
    >>>    shredder.publish(results)
    >>>
    >>> function aggregator(results):
    >>>    dosomethingwitresults
    >>>
    >>>  shredder = Shredder(
    >>>         work_generator=work_generator,
    >>>         worker=worker,
    >>>         aggregator=aggregator,
    >>>  )
    >>>
    >>>  shredder.start()
    >>>
