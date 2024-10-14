class SendMessage:
    def __init__(self, msg: str):
        self.msg = msg

    def __enter__(self):
        print(self.msg, end="\r")

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(" " * len(self.msg), end="\r")