import os
from subprocess import call

dir_path = os.path.dirname(os.path.realpath(__file__))

def stop():
    print('stopping container')
    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-compose.yaml'), 'down', '--remove-orphans'])


if __name__ == "__main__":
    stop()
