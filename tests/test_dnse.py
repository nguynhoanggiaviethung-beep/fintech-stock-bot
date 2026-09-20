from data.dnse_client import DNSEDataClient


def main():
    dnse = DNSEDataClient()

    print("DNSE client initialized successfully.")
    print("Client:", dnse.client)


if __name__ == "__main__":
    main()