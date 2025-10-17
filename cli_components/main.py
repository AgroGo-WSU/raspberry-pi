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
            display_startup(True)
        elif state == "dashboard":
            display_dashboard()
        
        print("\nPress 'q' to quit or Enter to refresh.")
        user_input = input("> ").strip().lower()
        if user_input == "q":
            print("Exiting program.")
            break

        time.sleep(0.1)  # Small buffer for readability

if __name__ == "__main__":
    main()