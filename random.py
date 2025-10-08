import random


ASCII_ART = r"""
  ____                 _                 _              
 |  _ \ __ _ _ __ ___ (_) ___  _ __ ___ | |__   ___ _ __ 
 | |_) / _` | '_ ` _ \| |/ _ \| '_ ` _ \| '_ \ / _ \ '__|
 |  _ < (_| | | | | | | | (_) | | | | | | |_) |  __/ |   
 |_| \_\__,_|_| |_| |_|_|\___/|_| |_| |_|_.__/ \___|_|   
"""


def main():
    number = random.randint(1, 100)
    print(ASCII_ART)
    print(f"Your random number between 1 and 100 is: {number}")


if __name__ == "__main__":
    main()
