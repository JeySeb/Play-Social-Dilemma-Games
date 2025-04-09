import json
import base64
import paho.mqtt.client as mqtt
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import cv2
import threading
import queue
import time

class DataSubscriber:
    def __init__(self, broker_address, data_topic, data_queue, gui, port):
        self.broker_address = broker_address
        self.data_topic = data_topic
        self.data_queue = data_queue
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.gui = gui  
        print(f"Trying to connect to {self.broker_address} on port {self.port}")
        self.client.connect(self.broker_address, self.port, 60)
        self.client.loop_start()
        

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Conectado al broker MQTT")
            client.subscribe(self.data_topic)
        else:
            print(f"Error al conectar al broker. Código de error: {rc}")

    def on_message(self, client, userdata, message):
        try:
            msg_json = message.payload.decode('utf-8')
            data_dict = json.loads(msg_json)
            self.data_queue.put(data_dict)

        except json.JSONDecodeError as e:
            print(f"Error al decodificar el mensaje JSON: {e}")

class ActionPublisher:
    def __init__(self, broker_address, actions_topic, port):
        self.broker_address = broker_address
        self.actions_topic = actions_topic
        self.port = port

        self.client = mqtt.Client()
        print(f"Action publisher trying to connect to {self.broker_address} on port {self.port}")
        self.client.connect(self.broker_address, self.port, 60)
        self.client.loop_start()

    def publish_action(self, agent_id, action):
        action_dict = {
            "agent_id": agent_id,
            "action": action
        }
        action_json = json.dumps(action_dict)
        self.client.publish(self.actions_topic, action_json)

class PlayerGUI:
    def __init__(self, root, data_queue, action_publisher, agent_id, show_only_self=True):
        self.root = root
        self.data_queue = data_queue
        self.action_publisher = action_publisher
        self.agent_id = agent_id
        self.show_only_self = show_only_self
        self.start_time = None
        self.timer_label = None
        self.game_started = False

        self.root.configure(bg='#2C2F33')
        self.root.title("Player Interface")
        self.root.geometry("1000x1000")
        
        # Crear un contenedor principal
        self.main_container = tk.Frame(self.root, bg='#2C2F33')
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create start screen frame dentro del contenedor principal
        self.start_frame = tk.Frame(self.main_container, bg='#23272A')
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create start button
        start_button = tk.Button(self.start_frame, text="START GAME",
                                 command=self.start_game,
                                 font=('Arial', 20, 'bold'),
                                 bg='#43B581', fg='white',
                                 width=15, height=3,
                                 relief=tk.RAISED, borderwidth=5)
        start_button.pack(expand=True)

        # Create main game frame dentro del contenedor principal pero no lo empaquetes aún
        self.game_frame = tk.Frame(self.main_container, bg='#2C2F33')
        self.frame = tk.Frame(self.game_frame, bg='#2C2F33')
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add timer label at the top
        self.timer_label = tk.Label(self.frame, text="Time: 00:00", bg='#2C2F33', fg='white', font=('Arial', 14))
        self.timer_label.pack(anchor='nw', padx=5, pady=5)

        
        self.labels = []
        self.img_resolution = (1000, 1000)

        self.player_names = ["Player 1", "Player 2"]
        self.number_of_players = 1 if show_only_self else 2

        self.text_scroll = None
        self.load_initial_images()
        self.create_bottom_space()
        self.create_control_panel()
        self.bind_keyboard_controls()
        self.able_to_move = False
        self.current_text = ""
        self.check_queue()
        self.update_timer()
        
    def check_server_response(self):
        if self.game_started:
            # Check if "go ahead" is in the text field
            self.game_started = True
            self.start_frame.destroy()
            self.game_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.root.after(100, self.check_server_response)
    
    def start_game(self):
        self.action_publisher.publish_action(self.agent_id, "start")
        # Wait for server confirmation
        self.check_server_response()

    def reset_game(self):
        # Reset timer
        self.start_time = None
        self.game_started = False
        
        # Destroy all frames
        self.game_frame.destroy()
        if hasattr(self, 'bottom_space'):
            self.bottom_space.destroy()
        if hasattr(self, 'control_panel'):
            self.control_panel.destroy()
        
        # Recreate start frame and button
        self.start_frame = tk.Frame(self.main_container, bg='black')
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        
        start_button = tk.Button(self.start_frame, text="START GAME",
                               command=self.start_game,
                               font=('Arial', 30, 'bold'),
                               bg='green', fg='white',
                               width=20, height=5)
        start_button.pack(expand=True)
        
        # Recreate game frame but don't pack it yet
        self.game_frame = tk.Frame(self.main_container, bg='#2C2F33')
        self.frame = tk.Frame(self.game_frame, bg='#2C2F33')
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Reset all other components
        self.timer_label = tk.Label(self.frame, text="Time: 00:00", bg='#2C2F33', font=('Arial', 12))
        self.timer_label.pack(anchor='nw', padx=5, pady=5)
        
        self.labels = []
        self.load_initial_images()
        self.create_bottom_space()
        self.create_control_panel()

    def update_timer(self):
        if self.start_time is not None:
            elapsed_time = int(time.time() - self.start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            self.timer_label.config(text=f"Time: {minutes:02d}:{seconds:02d}")
        self.root.after(1000, self.update_timer)

    def create_bottom_space(self):
        self.bottom_space = tk.Frame(self.root, bg='#23272A')
        self.bottom_space.pack(fill=tk.X, expand=False, pady=10)

        self.text_scroll = tk.Text(self.bottom_space, wrap=tk.NONE, height=5, width=70,
                                   bg='#99AAB5', fg='black', font=('Arial', 12))
        self.text_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.text_scroll.config(state='disabled')

        self.bottom_space.pack(fill=tk.X, expand=False, pady=10)
        
    def load_initial_images(self):
        # Create arrow images
        arrow_size = (30, 30)
        
        # Up arrow
        up_arrow = np.zeros((*arrow_size, 3), dtype=np.uint8)
        cv2.arrowedLine(up_arrow, (15, 25), (15, 5), (255, 255, 255), 2, tipLength=0.4)
        self.up_img = ImageTk.PhotoImage(Image.fromarray(up_arrow))

        # Down arrow  
        down_arrow = np.zeros((*arrow_size, 3), dtype=np.uint8)
        cv2.arrowedLine(down_arrow, (15, 5), (15, 25), (255, 255, 255), 2, tipLength=0.4)
        self.down_img = ImageTk.PhotoImage(Image.fromarray(down_arrow))

        # Left arrow
        left_arrow = np.zeros((*arrow_size, 3), dtype=np.uint8)
        cv2.arrowedLine(left_arrow, (25, 15), (5, 15), (255, 255, 255), 2, tipLength=0.4)
        self.left_img = ImageTk.PhotoImage(Image.fromarray(left_arrow))

        # Right arrow
        right_arrow = np.zeros((*arrow_size, 3), dtype=np.uint8)
        cv2.arrowedLine(right_arrow, (5, 15), (25, 15), (255, 255, 255), 2, tipLength=0.4)
        self.right_img = ImageTk.PhotoImage(Image.fromarray(right_arrow))

        # Fire button
        fire_img = np.zeros((*arrow_size, 3), dtype=np.uint8)
        cv2.circle(fire_img, (15, 15), 10, (0, 0, 255), -1)
        self.fire_img = ImageTk.PhotoImage(Image.fromarray(fire_img))

        
        # Add rotation arrows
        rotate_size = (30, 30)
        
        # Rotate left arrow (curved arrow pointing left)
        rotate_left = np.zeros((*rotate_size, 3), dtype=np.uint8)
        cv2.ellipse(rotate_left, (15, 15), (10, 10), 0, 0, 300, (255, 255, 255), 2)
        cv2.arrowedLine(rotate_left, (8, 15), (5, 15), (255, 255, 255), 2, tipLength=0.4)
        self.rotate_left_img = ImageTk.PhotoImage(Image.fromarray(rotate_left))

        # Rotate right arrow (curved arrow pointing right)
        rotate_right = np.zeros((*rotate_size, 3), dtype=np.uint8)
        cv2.ellipse(rotate_right, (15, 15), (10, 10), 0, -120, 180, (255, 255, 255), 2)
        cv2.arrowedLine(rotate_right, (22, 15), (25, 15), (255, 255, 255), 2, tipLength=0.4)
        self.rotate_right_img = ImageTk.PhotoImage(Image.fromarray(rotate_right))


        # Initialize player images
        for _ in range(self.number_of_players):
            img_array = np.zeros((350, 350, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            photo = ImageTk.PhotoImage(image=img)
            label = tk.Label(self.frame, image=photo)
            label.image = photo
            self.labels.append(label)
            label.pack()
            
      
    def create_control_panel(self):
        self.control_panel = tk.Frame(self.root, bg='#23272A')
        self.control_panel.pack(fill=tk.X, expand=False, pady=10)

        # Create main movement controls frame
        movement_frame = tk.Frame(self.control_panel, bg='#23272A')
        movement_frame.pack(side=tk.LEFT, padx=20)

        # Create rotation controls frame
        rotation_frame = tk.Frame(self.control_panel, bg='#23272A')
        rotation_frame.pack(side=tk.RIGHT, padx=20)

        # Movement controls
        button_up = tk.Button(movement_frame, image=self.up_img, command=lambda: self.handle_action("up"), bg='#7289DA', fg='white', borderwidth=3)
        button_down = tk.Button(movement_frame, image=self.down_img, command=lambda: self.handle_action("down"), bg='#7289DA', fg='white', borderwidth=3)
        button_left = tk.Button(movement_frame, image=self.left_img, command=lambda: self.handle_action("left"), bg='#7289DA', fg='white', borderwidth=3)
        button_right = tk.Button(movement_frame, image=self.right_img, command=lambda: self.handle_action("right"), bg='#7289DA', fg='white', borderwidth=3)
        button_fire = tk.Button(movement_frame, image=self.fire_img, command=lambda: self.handle_action("firezap"), bg='#7289DA', fg='white', borderwidth=3)

        # Ubicar botones de movimiento
        button_up.grid(row=0, column=1, pady=5)
        button_left.grid(row=1, column=0, padx=5)
        button_fire.grid(row=1, column=1, padx=5, pady=5)
        button_right.grid(row=1, column=2, padx=5)
        button_down.grid(row=2, column=1, pady=5)

        # Rotation controls
        button_rotate_left = tk.Button(rotation_frame, image=self.rotate_left_img, 
                                    command=lambda: self.handle_action("turn left"))
        button_rotate_right = tk.Button(rotation_frame, image=self.rotate_right_img, 
                                    command=lambda: self.handle_action("turn right"))
        
        # Label for rotation controls
        rotation_label = tk.Label(rotation_frame, text="Rotation", bg='#23272A', fg='white')
        rotation_label.pack(pady=5)
        
        # Pack rotation buttons
        button_rotate_left.pack(side=tk.LEFT, padx=5)
        button_rotate_right.pack(side=tk.RIGHT, padx=5)


    def bind_keyboard_controls(self):
        self.root.bind('<Left>', lambda event: self.handle_action("move left"))
        self.root.bind('<Right>', lambda event: self.handle_action("move right"))
        self.root.bind('<Up>', lambda event: self.handle_action("move up"))
        self.root.bind('<Down>', lambda event: self.handle_action("move down"))
        self.root.bind('<space>', lambda event: self.handle_action("attack"))
        self.root.bind('z', lambda event: self.handle_action("turn left"))
        self.root.bind('x', lambda event: self.handle_action("turn right"))

    def handle_action(self, action):
        if self.able_to_move and self.game_started:
            self.action_publisher.publish_action(self.agent_id, action)


    def update_action_text(self, text):
        self.right_panel.config(state=tk.NORMAL)
        self.right_panel.delete(1.0, tk.END)
        self.right_panel.insert(tk.END, text)
        self.right_panel.config(state=tk.DISABLED)

    def execute_action(self):
        action_text = self.right_panel.get("1.0", tk.END).strip()
        if action_text:
            # Publicar el contenido del label al tópico 'actions'
            self.action_publisher.publish_action(self.agent_id, action_text)
            # Restablecer los botones y limpiar el campo de acción
            for widget in self.left_panel.winfo_children():
                widget.destroy()
            self.add_action_buttons()
            self.update_action_text("")  # Limpia el label después de ejecutar
        
    def choose_player(self, action):
        player_name = self.listbox.get(self.listbox.curselection())
        self.update_action_text(f"{action} {player_name}")

        for widget in self.left_panel.winfo_children():
            if isinstance(widget, tk.Listbox) or isinstance(widget, tk.Button):
                widget.destroy()

        label = tk.Label(self.left_panel, text="Enter position to attack:")
        label.pack()
        entry = tk.Entry(self.left_panel)
        entry.pack()

        button = tk.Button(self.left_panel, text="Set attack position", command=lambda: self.update_action_text(f"{action} {player_name} at position {entry.get()}"))
        button.pack()
        
        
    def update_gui(self, data_dict):
        # Check for end game message
        for agent_id in data_dict:
            if data_dict[agent_id].get("end_game", False):
                self.reset_game()
                return
            elif data_dict[agent_id].get("game_started", False) and not self.game_started:
                self.game_started = True
                self.start_game()
                return
        
        
        
        # Start timer when first image is received
        if self.start_time is None:
            self.start_time = time.time()
            
        sorted_agents = sorted(data_dict.keys())
        
        for i, agent_id in enumerate(sorted_agents):
            # Skip if we're only showing self and this isn't our agent
            if self.show_only_self and agent_id != self.agent_id:
                continue
                
            agent_data = data_dict[agent_id]
            is_turn = agent_data.get("is_turn", False)
            image_base64 = agent_data.get("image", "")
            text = agent_data.get("text", "")
            orientation = agent_data.get("orientation", "0")

            # Calculate the correct label index
            label_index = 0 if self.show_only_self else i

            img_data = base64.b64decode(image_base64)
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img_array = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            img_resized = cv2.resize(img_array, self.img_resolution, interpolation=cv2.INTER_NEAREST)
            
            
            # Resize to 400x400 with Lanczos interpolation for high quality downscaling
            img_resized_small = cv2.resize(img_resized, (400, 400), interpolation=cv2.INTER_LANCZOS4)
            img_resized = img_resized_small
            
            if orientation == "1":  # Right - rotate left once
                img_resized = np.rot90(img_resized, 1)
            elif orientation == "2":  # Down - rotate left twice
                img_resized = np.rot90(img_resized, 2)
            elif orientation == "3":  # Left - rotate left three times
                img_resized = np.rot90(img_resized, 3)
            # orientation == 0 means up, no rotation needed

            img = Image.fromarray(img_resized)
            photo = ImageTk.PhotoImage(image=img)
            label = self.labels[label_index]
            label.configure(image=photo)
            label.image = photo

            if is_turn:
                label.config(borderwidth=5, relief="solid", highlightthickness=5, highlightbackground="green")
                if agent_id == self.agent_id:
                    self.update_text(text)
                    self.able_to_move = True
                else:
                    self.able_to_move = False
            else:
                label.config(borderwidth=5, relief="solid", highlightthickness=0)
                if agent_id == self.agent_id:
                    self.able_to_move = False

    def update_text(self, text):
        self.current_text = f"Texto: {text}"
        self.text_scroll.config(state='normal')
        self.text_scroll.delete(1.0, tk.END)
        self.text_scroll.insert(tk.END, self.current_text)
        self.text_scroll.config(state='disabled')
        self.root.update()

    def check_queue(self):
        while not self.data_queue.empty():
            data_dict = self.data_queue.get()
            self.update_gui(data_dict)
        self.root.after(100, self.check_queue)
        
        
def main(port: int, agent_id: str="1"):
    broker_address = "172.24.98.252"  # Cambia esta dirección según sea necesario
    data_topic = "topic/data"
    actions_topic = "topic/actions"

    data_queue = queue.Queue()

    action_publisher = ActionPublisher(broker_address, actions_topic, port)

    root = tk.Tk()
    gui = PlayerGUI(root, data_queue, action_publisher, agent_id)
    
    subscriber = DataSubscriber(broker_address, data_topic, data_queue, gui, port)
    
    root.mainloop()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8085)
    parser.add_argument("--agent_id", type=str, default="1")
    args = parser.parse_args()
    
    main(args.port, args.agent_id)
