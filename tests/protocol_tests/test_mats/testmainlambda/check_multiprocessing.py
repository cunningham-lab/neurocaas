import time
import multiprocessing

def foo(i):
    time.sleep(i)

TIMEOUT = 1 

if __name__ == '__main__':
    p = multiprocessing.Process(target=foo, name="Foo",args = [5])
    p.start()

    p.join(TIMEOUT)

    if p.is_alive():
        print('function terminated')
        p.terminate()
        p.join()
