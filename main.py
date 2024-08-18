import cv2
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
import requests
import threading
import time

class IPWebcamApp:
    def __init__(self, root, url, esp32_ip):
        self.root = root
        self.root.title("IP Webcam Stream")
        self.url = url
        self.esp32_ip = esp32_ip
        self.cap = cv2.VideoCapture(self.url)

        if not self.cap.isOpened():
            print("Error: Unable to open video stream")
            return

        self.path = []
        self.is_recording = False
        self.start_time = None

        # Configure the root window's grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=1)

        # Create a frame for the video display
        self.video_frame = ttk.Frame(root)
        self.video_frame.grid(row=0, column=0, sticky="nsew")

        # Video display label
        self.label = ttk.Label(self.video_frame)
        self.label.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the keyboard arrow keys layout
        self.arrow_keys_frame = ttk.Frame(root, padding="10")
        self.arrow_keys_frame.grid(row=0, column=1, sticky="ns")

        # Add text "Control Keys" above the keys
        control_label = ttk.Label(self.arrow_keys_frame, text="Control Keys", font=("Helvetica", 25, "bold"))
        control_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # Canvas size for each key
        canvas_size = 90

        # Triangle size
        triangle_size = 60

        # Create a canvas for each arrow key and draw triangles with boundary boxes
        self.up_canvas = tk.Canvas(self.arrow_keys_frame, width=canvas_size, height=canvas_size)
        self.down_canvas = tk.Canvas(self.arrow_keys_frame, width=canvas_size, height=canvas_size)
        self.left_canvas = tk.Canvas(self.arrow_keys_frame, width=canvas_size, height=canvas_size)
        self.right_canvas = tk.Canvas(self.arrow_keys_frame, width=canvas_size, height=canvas_size)

        # Draw triangles and boundary boxes on the canvases
        self.up_canvas.create_rectangle(5, 5, canvas_size-5, canvas_size-5, outline="black", width=4)
        self.up_canvas.create_polygon(canvas_size//2, 10, canvas_size//2 - triangle_size//2, canvas_size - 10,
                                       canvas_size//2 + triangle_size//2, canvas_size - 10, fill="black")

        self.down_canvas.create_rectangle(5, 5, canvas_size-5, canvas_size-5, outline="black", width=4)
        self.down_canvas.create_polygon(canvas_size//2, canvas_size - 10, canvas_size//2 - triangle_size//2, 10,
                                         canvas_size//2 + triangle_size//2, 10, fill="black")

        self.left_canvas.create_rectangle(5, 5, canvas_size-5, canvas_size-5, outline="black", width=4)
        self.left_canvas.create_polygon(10, canvas_size//2, canvas_size - 10, canvas_size//2 - triangle_size//2,
                                        canvas_size - 10, canvas_size//2 + triangle_size//2, fill="black")

        self.right_canvas.create_rectangle(5, 5, canvas_size-5, canvas_size-5, outline="black", width=4)
        self.right_canvas.create_polygon(canvas_size - 10, canvas_size//2, 10, canvas_size//2 - triangle_size//2,
                                         10, canvas_size//2 + triangle_size//2, fill="black")

        # Arrange canvases in a grid
        self.up_canvas.grid(row=3, column=1, pady=5)
        self.left_canvas.grid(row=4, column=0, padx=5)
        self.right_canvas.grid(row=4, column=2, padx=5)
        self.down_canvas.grid(row=4, column=1, pady=5)

        # Keyboard bindings for controlling the robot
        self.root.bind('<Up>', lambda event: self.send_command('up'))
        self.root.bind('<Down>', lambda event: self.send_command('down'))
        self.root.bind('<Left>', lambda event: self.send_command('left'))
        self.root.bind('<Right>', lambda event: self.send_command('right'))

        # Record and Replay buttons
        self.record_button = ttk.Button(self.arrow_keys_frame, text="Record Path", command=self.toggle_record)
        self.record_button.grid(row=5, column=0, pady=5)

        self.replay_button = ttk.Button(self.arrow_keys_frame, text="Replay Path", command=self.replay_path)
        self.replay_button.grid(row=5, column=2, pady=5)

        self.reset_button = ttk.Button(self.arrow_keys_frame, text="Reset Path", command=self.reset_path)
        self.reset_button.grid(row=6, column=1, pady=5)

        # Capture button
        self.capture_button = ttk.Button(self.arrow_keys_frame, text="Capture Image", command=self.capture_image)
        self.capture_button.grid(row=7, column=1, pady=5)

        self.update_frame()

    def toggle_record(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.start_time = time.time()
            self.path = []  # Clear previous path
            self.record_button.config(text="Stop Recording")
        else:
            self.record_button.config(text="Record Path")
            print("Recording stopped. Path:", self.path)

    def send_command(self, direction):
        url = f"http://{self.esp32_ip}/move?direction={direction}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Command {direction} sent successfully")
                if self.is_recording:
                    timestamp = time.time() - self.start_time
                    self.path.append((direction, timestamp))
            else:
                print(f"Failed to send command {direction}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending command {direction}: {e}")

    def replay_path(self):
        if not self.path:
            print("No path to replay.")
            return

        def replay():
            replay_start_time = time.time()
            for command, timestamp in self.path:
                while time.time() - replay_start_time < timestamp:
                    time.sleep(0.01)
                self.send_command(command)

            print("Path replay completed. Pausing for 2 minutes.")
            time.sleep(0.5 * 60)  # Pause for 2 minutes

            # Turn right 180 degrees
            print("Turning 180 degrees right")
            self.send_command('right')
            time.sleep(2)  # Adjust this delay based on your robot's turning speed

            print("Reversing path.")
            reversed_path = self.path[::-1]  # Reverse the path

            replay_start_time = time.time()
            for command, timestamp in reversed_path:
                while time.time() - replay_start_time < timestamp:
                    time.sleep(0.01)
                reversed_command = self.get_reverse_command(command)
                self.send_command(reversed_command)

        threading.Thread(target=replay).start()

    def get_reverse_command(self, command):
        reverse_mapping = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        }
        return reverse_mapping.get(command, command)

    def reset_path(self):
        self.path = []
        print("Path reset.")

    def capture_image(self):
        ret, frame = self.cap.read()
        if ret:
            filename = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                    filetypes=[("JPEG files", ".jpg"), ("All files", ".*")])
            if filename:
                cv2.imwrite(filename, frame)
                print(f"Image saved as {filename}")

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert the frame to an image format compatible with tkinter
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.label.imgtk = imgtk
            self.label.configure(image=imgtk)

        # Repeat this process after 10 ms
        self.root.after(10, self.update_frame)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

def main():
    # Replace with your IP address and port
    ip_address = '192.168.1.11'
    port = '8080'
    url = f"http://{ip_address}:{port}/video"

    # Replace with your ESP32 IP address
    esp32_ip = '192.168.1.14'

    root = tk.Tk()
    app = IPWebcamApp(root, url, esp32_ip)
    root.mainloop()

if __name__ == '__main__':
    main()