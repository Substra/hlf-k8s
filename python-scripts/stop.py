from subprocess import call


def stop():
    print('stopping container')
    call(['docker-compose', '-f', '../docker-compose.yaml', 'down', '--remove-orphans'])


if __name__ == "__main__":
    stop()
