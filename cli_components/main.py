import time
from startup import display_startup
from dashboard import display_dashboard

def main():  
    state = "startup"

    while True:
        print("\n==============================")
        print(f"Current state: {state}")
        print("==============================")

        if state == "startup":
            state = display_startup(True)
        elif state == "dashboard":
            display_dashboard()

        time.sleep(0.1)  # Small buffer for readability

if __name__ == "__main__":
    main()