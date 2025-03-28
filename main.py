from host import Host


def main():
    print("Hello there, I'm the host of the talkshow.")
    topic = input("What do you want to discuss today? ")
    host = Host(topic, display_mode="console")


if __name__ == "__main__":
    main()
