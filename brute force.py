from pwn import *
import time
import re
import random

#part of pwn, removes extra info in the conn
#remove when debugging
context.log_level = "error"

CALLS = 1 # to keep track for seeds

HOST = "94.237.53.203"
PORT = 36317

MAX_WAIT = 60 #Find a wait time no more than 60 sec
MIN_WAIT = 16 #and no shorter than 16 seconds (time for server to reply)

#Copied from game's code
#Generates seed for the game based in the initial seed, which is derived from the time and MAC
def lcg(seed, a=1664525, c=1013904223, m=2 ** 32):
    return (a * seed + c) % m

#Copied from game's code
#Generates two ID values that are used for determining if a poketmon is shiny
def generate_ids(seed):
    random.seed(seed)
    tid = random.randint(0, 65535)
    sid = random.randint(0, 65535)
    return tid, sid

#Copied from game's code
#Removed values that are not necessary for determining if a poketmon is shiny
def generate_poketmon(seed, tid, sid):
    random.seed(seed)
    stats = {
        "HP": random.randint(20, 31),
        "Attack": random.randint(20, 31),
        "Defense": random.randint(20, 31),
        "Speed": random.randint(20, 31),
        "Special Attack": random.randint(20, 31),
        "Special Defense": random.randint(20, 31)
    }
    natures = ["Adamant", "Bashful", "Bold", "Brave", "Calm", "Careful", "Docile", "Gentle", "Hardy", "Hasty", "Impish",
               "Jolly", "Lax", "Lonely", "Mild", "Modest", "Naive", "Naughty", "Quiet", "Quirky", "Rash", "Relaxed",
               "Sassy", "Serious", "Timid"]
    nature = random.choice(natures)
    pid = random.randint(0, 2 ** 32 - 1)
    shiny_value = ((tid ^ sid) ^ (pid & 0xFFFF) ^ (pid >> 16))
    generate_poketmon = shiny_value < 8 #value contains boolean is pokemon is shiny

    return generate_poketmon

#Extracts MAC address from the game's output
def extract_mac(conn):
    while True:
        mac = conn.recvline().decode().strip()
        match = re.search(r"Mac Address:\s*([a-f0-9:]+)", mac)
        if match:
            return match.group(1)

#Main function to perform Brute Force attack
#Loops through the game until a shiny poketmon is found and gets the exact values to get a shiny poketmon       
#partially coped from main function form game script
def find_valid_seed(mac):
    mac_int = int(mac.replace(":", ""), 16)
    attempt = 1 #reseted for each seed

    for time_passed in range(MIN_WAIT, MAX_WAIT + 1):
        initial_seed = mac_int + time_passed #computes the initial seed based on mac and address
        seed = lcg(initial_seed) #computes seed based on lcg function
        tid, sid = generate_ids(seed)

        #testing all 3 starter poketmon
        for i in range(3):
            is_shiny = generate_poketmon(seed + i, tid, sid) #gets boolean value for shiny
            if is_shiny: #if it is shiny, it returns time required to wait and starter poketmon choice
                print(f"Seed #{CALLS}: Attempt #{attempt}: Time: {time_passed} seconds, choice {i + 1} → {is_shiny}")
                return time_passed, str(i + 1)
    
    attempt += 1
    return None, None

def interact(conn, shiny_time, choice):
    print("Starting game...") #for us that game has started
    conn.recvuntil(b"First, what is your name?")
    time.sleep(shiny_time - 16)
    conn.sendline(b"pwn") #dummy response

    conn.recvuntil(b"Choose your starter Poketmon (1, 2, or 3):")
    conn.sendline(choice.encode())

    while True:
        decision = conn.recvline() #line in terminal that depends if shiny is obtained or not
        if b"Congratulations! You have obtained a shiny Poketmon!" in decision:
            conn.recvuntil(b"HTB")
            flag = conn.recvuntil(b"}").decode() #retrive flag
            print("FLAG:", flag)
            break
        elif b"Good luck" in decision:
            print("Not shiny.") #parameters were found but there is a bug
            break

def main():
    while True:
        conn = remote(HOST, PORT) #connect to server
        mac = extract_mac(conn)
        global CALLS #allows us to modify the global variable

        #we can change the max value for a shorter time
        #min value had to be  greater than 16
        #if shiny time is not within this time range, the parameters are computer again until a better time is found
        shiny_time, choice = find_valid_seed(mac)
        CALLS += 1
        if shiny_time is None:
            print(f"Seed #{CALLS - 1}: No shiny found in valid time range. Retrying...")
            conn.close()
            continue #parameters not found where wait time is 16 < t < 100

        print(f"Shiny found at {shiny_time}s, pick #{choice}") 
        interact(conn, shiny_time, choice) #plays game with given shiny parameters
        break

if __name__ == "__main__":
    main()
