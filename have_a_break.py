'''To play a video clip every 60 (by default) or custom mins to remind you to have a break'''

import subprocess
import time
import threading
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import win32api
import win32gui
import win32con
import tkinter as tk
from tkinter import simpledialog

# Path to VLC and your video file
vlc_path = r"D:\Program Files (x86)\VideoLAN\VLC\vlc.exe"  # Update if needed
video_path = r"C:\technical learning\Python\Health_song_Fxx.mp4"

#the minutes and seconds to pass to have a break periodically,default is 60 minutes  
time_set = (59,60)

#read from a configuration file the stored time_set
try:
    with open('./break_timeset.txt','r') as f_btime:
        line = f_btime.readline()
        try:
            min,sec=map(int,line.strip().split())
            if 0 <= min <= 60 and 0 <= sec <= 60:
                time_set=(min,sec)
            else:
                print('incorrect min and sec in ./break_timeset.txt')
        except Exception:
            print('incorrect data format in ./break_timeset.txt')
except FileNotFoundError:
    print('./break_timeset.txt not found')

# Global variable to track time left
time_left = list(time_set)
keep_run = True

'''since time_set and time_left can be set manually, and multithreads may read/write 
time_left simultaneously, lock is needed'''
time_left_lock = threading.Lock()

#a pop up dialog to set the time_set
def set_timer(icon, item):
    #after the user clicking the set button
    def validate_and_set_time():
        nonlocal root, error_label
        try:
            minutes = int(minute_input.get())
            seconds = int(second_input.get())
            #print(minutes,seconds)
            # Validate range [0, 60]
            if 0 <= minutes <= 60 and 0 <= seconds <= 60:
                with time_left_lock:
                    global time_set,time_left
                    time_set=(minutes,seconds)
                    time_left=list(time_set)  #each time_set is set, time_let needs to update accordingly
                    #print(time_left)
                root.destroy()  # Close dialog if input is valid
            else:
                error_label.config(text="Minutes and seconds must be between 0 and 60!")
        except ValueError:
            error_label.config(text="Please enter valid integers!")

    #create the dialog
    root = tk.Tk()
    root.title("Set Timer")
    root.geometry("300x200")
    # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate position x and y to center the window
    window_width = 300
    window_height = 200
    position_x = (screen_width // 2) - (window_width // 2)
    position_y = (screen_height // 2) - (window_height // 2)

    # Set the geometry to center the window
    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    tk.Label(root, text="Set Timer").pack(pady=5)

    tk.Label(root, text="Minutes (0-60):").pack()
    minute_input = tk.Entry(root)
    minute_input.pack()

    tk.Label(root, text="Seconds (0-60):").pack()
    second_input = tk.Entry(root)
    second_input.pack()

    error_label = tk.Label(root, text="", fg="red")  # Label for error messages
    error_label.pack(pady=5)
    #set the button call-back method to validate_and_set_time
    tk.Button(root, text="Set", command=validate_and_set_time).pack(pady=10)

    root.mainloop()
    
def create_image():
    # Load an existing image for the tray icon
    icon_path = r"C:\technical learning\Python\take-break-icon.png"  # Path to your image file (e.g., .png or .ico)
    return Image.open(icon_path)

def stop_program(icon, item):
    # Stop the video playback and exit the program
    global keep_run
    icon.stop()
    keep_run=False


def start_tray_icon(icon):
    # Create the system tray icon with a menu
    icon.run()

def start_play_video():
     subprocess.run([vlc_path, video_path])

myicon = Icon("VideoPlayer", create_image())
# Start the tray icon in a separate thread
tray_thread = threading.Thread(target=start_tray_icon, args=[myicon],daemon=True)
tray_thread.start()

#the class used to handle event of computer waking up from hibernation
class PowerEventHandler:
    def __init__(self):
        self.internal_variable = 0
    
    def handle_event(self, hwnd, msg, wparam, lparam):
        global time_left
        if msg == win32con.WM_POWERBROADCAST and wparam == win32con.PBT_APMRESUMEAUTOMATIC:
            #print("Laptop woke up from hibernation!")
            time_left = [59,60]
        return True
    
'''creates a custom Windows Message Handling Window'''
handler = PowerEventHandler()
wc = win32gui.WNDCLASS()
wc.lpszClassName = 'PowerHandler'
wc.hInstance = win32api.GetModuleHandle(None)
wc.lpfnWndProc = handler.handle_event

class_atom = win32gui.RegisterClass(wc)
#create a window of the registered class with no size and invisible
hwnd = win32gui.CreateWindow(class_atom, 'PowerHandler', 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)

def update_tray_menu(icon):
    # Update the menu with the remaining time
    global time_left
    #the tray menu has three items, time left, set timer, and stop
    menu = Menu(
        MenuItem(f"Time left: {time_left[0]} minutes {time_left[1]} seconds", lambda icon,item:None),
        MenuItem('Set Timer', set_timer),  # Add the new menu option here
        MenuItem('Stop', action=stop_program)
    )
    icon.menu = menu
    
    #the title will show when you mouse over the icon
    icon.title = f"{time_left}"

#the main loop to update the time_left and start playing the video every pre-set period
while keep_run:
        with time_left_lock:
            update_tray_menu(myicon) #you can see the update of time_left instantly
        #process pending messages if any
        win32gui.PumpWaitingMessages()
        with time_left_lock:
            if time_left[0]==-1: #it's the time for a break
                video_play_thread = threading.Thread(target=start_play_video)
                video_play_thread.start()
                time_left = list(time_set)  # Reset time left
        
        time.sleep(1)
        with time_left_lock:  
            if time_left[1]==0:
                time_left[1]=60
                time_left[0]-=1
            time_left[1] -= 1 
#destroy the window of registered class
win32gui.DestroyWindow(hwnd)

#store time_set to the configuration file
try:
    with open('./break_timeset.txt','w') as f_btime:
        f_btime.write(str(time_set[0])+' '+str(time_set[1]))
except Exception as e:
    print(f'open ./break_timeset.txt for write error {e}')


