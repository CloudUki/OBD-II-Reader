import obd
import time
import os
import sys
import argparse
from datetime import datetime

# Trying to importing GUI libraries
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import threading
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("GUI libraries not available. Running in terminal mode only.")

def clear_screen():
    os.system('clear')

def terminal_mode():
    """Run OBD reader in terminal mode"""
    print("Connecting to OBD-II port...")
    
    # Try specific port first if not auto detect
    connection = None
    
    # Try /dev/ttyACM0 first (Drew Technologies adapter)
    try:
        print("Trying /dev/ttyACM0...")
        connection = obd.OBD('/dev/ttyACM0', timeout=30)
        if connection.is_connected():
            print("Connected via /dev/ttyACM0!")
    except:
        pass
    
    # If that failed, try auto-detect
    if not connection or not connection.is_connected():
        print("Trying auto-detection...")
        connection = obd.OBD()
    
    if not connection.is_connected():
        print("Failed to connect to vehicle!")
        print("Check:")
        print("- OBD-II adapter is plugged in")
        print("- Vehicle ignition is ON")
        print("- Adapter drivers are installed")
        return
    
    print(f"Connected to: {connection.port_name()}")
    print("Protocol:", connection.protocol_name())
    print("\nStarting data read... (Press Ctrl+C to exit)")
    time.sleep(2)
    
    try:
        while True:
            clear_screen()
            print("=== OBD-II LIVE DATA ===")
            print("-" * 25)
            
            # Read RPM
            rpm_cmd = obd.commands.RPM
            rpm_response = connection.query(rpm_cmd)
            if rpm_response.value is not None:
                print(f"Engine RPM:      {rpm_response.value.magnitude:.0f} rpm")
            else:
                print("Engine RPM:      No data")
            
            # Read Speed
            speed_cmd = obd.commands.SPEED
            speed_response = connection.query(speed_cmd)
            if speed_response.value is not None:
                print(f"Vehicle Speed:   {speed_response.value.magnitude:.0f} mph")
            else:
                print("Vehicle Speed:   No data")
            
            # Read Coolant Temperature
            coolant_cmd = obd.commands.COOLANT_TEMP
            coolant_response = connection.query(coolant_cmd)
            if coolant_response.value is not None:
                temp_f = coolant_response.value.magnitude * 9/5 + 32
                print(f"Coolant Temp:    {coolant_response.value.magnitude:.1f}°C ({temp_f:.1f}°F)")
            else:
                print("Coolant Temp:    No data")
            
            # Read Throttle Position
            throttle_cmd = obd.commands.THROTTLE_POS
            throttle_response = connection.query(throttle_cmd)
            if throttle_response.value is not None:
                print(f"Throttle Pos:    {throttle_response.value.magnitude:.1f}%")
            else:
                print("Throttle Pos:    No data")
            
            # Read Engine Load
            load_cmd = obd.commands.ENGINE_LOAD
            load_response = connection.query(load_cmd)
            if load_response.value is not None:
                print(f"Engine Load:     {load_response.value.magnitude:.1f}%")
            else:
                print("Engine Load:     No data")
            
            # Read Intake Air Temperature
            iat_cmd = obd.commands.INTAKE_TEMP
            iat_response = connection.query(iat_cmd)
            if iat_response.value is not None:
                iat_f = iat_response.value.magnitude * 9/5 + 32
                print(f"Intake Air Temp: {iat_response.value.magnitude:.1f}°C ({iat_f:.1f}°F)")
            else:
                print("Intake Air Temp: No data")
            
            # Read Fuel Level
            fuel_cmd = obd.commands.FUEL_LEVEL
            fuel_response = connection.query(fuel_cmd)
            if fuel_response.value is not None:
                print(f"Fuel Level:      {fuel_response.value.magnitude:.1f}%")
            else:
                print("Fuel Level:      No data")
            
            print("-" * 25)
            print("Press Ctrl+C to exit")
            
            # Wait before next reading
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        connection.close()
        print("Connection closed.")

class OBDReaderGUI:
    """GUI version of OBD reader"""
    def __init__(self, root):
        self.root = root
        self.root.title("OBD-II Data Reader")
        self.root.geometry("800x600")
        self.root.configure(bg='#1e1e1e')
        
        # Connection variables
        self.connection = None
        self.is_running = False
        self.data_thread = None
        
        # Data storage
        self.data_vars = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg='#2d2d2d', height=80)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="OBD-II Data Reader", 
                              font=('Arial', 24, 'bold'), 
                              fg='white', bg='#2d2d2d')
        title_label.pack(pady=20)
        
        # Status frame
        status_frame = tk.Frame(self.root, bg='#1e1e1e')
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text="Status: Disconnected", 
                                   font=('Arial', 12), 
                                   fg='red', bg='#1e1e1e')
        self.status_label.pack(side='left')
        
        self.connect_btn = tk.Button(status_frame, text="Connect", 
                                   command=self.toggle_connection,
                                   font=('Arial', 10, 'bold'),
                                   bg='#4CAF50', fg='white',
                                   width=12)
        self.connect_btn.pack(side='right', padx=5)
        
        # Main data frame
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create data display grid
        self.create_data_displays(main_frame)
        
        # Footer with timestamp
        footer_frame = tk.Frame(self.root, bg='#2d2d2d', height=40)
        footer_frame.pack(fill='x', padx=10, pady=5)
        footer_frame.pack_propagate(False)
        
        self.time_label = tk.Label(footer_frame, text="", 
                                 font=('Arial', 10), 
                                 fg='#888888', bg='#2d2d2d')
        self.time_label.pack(pady=10)
        
        # Update timestamp
        self.update_timestamp()
        
    def create_data_displays(self, parent):
        # Data parameters to display
        parameters = [
            ("Engine RPM", "rpm", "RPM"),
            ("Speed", "speed", "MPH"),
            ("Coolant Temp", "coolant_temp", "°C"),
            ("Throttle Position", "throttle_pos", "%"),
            ("Engine Load", "engine_load", "%"),
            ("Intake Air Temp", "intake_temp", "°C"),
            ("Fuel Level", "fuel_level", "%"),
            ("Fuel Pressure", "fuel_pressure", "kPa")
        ]
        
        # Create grid layout (2 columns, 4 rows)
        for i, (display_name, var_name, unit) in enumerate(parameters):
            row = i // 2
            col = i % 2
            
            # Create frame for each parameter
            param_frame = tk.Frame(parent, bg='#2d2d2d', relief='raised', bd=2)
            param_frame.grid(row=row, column=col, padx=10, pady=10, 
                           sticky='nsew', ipadx=20, ipady=15)
            
            # Parameter name
            name_label = tk.Label(param_frame, text=display_name,
                                font=('Arial', 12, 'bold'),
                                fg='white', bg='#2d2d2d')
            name_label.pack()
            
            # Value display
            value_var = tk.StringVar(value="--")
            self.data_vars[var_name] = value_var
            
            value_label = tk.Label(param_frame, textvariable=value_var,
                                 font=('Arial', 20, 'bold'),
                                 fg='#00FF00', bg='#2d2d2d')
            value_label.pack(pady=5)
            
            # Unit label
            unit_label = tk.Label(param_frame, text=unit,
                                font=('Arial', 10),
                                fg='#888888', bg='#2d2d2d')
            unit_label.pack()
        
        # Configure grid weights
        for i in range(4):
            parent.grid_rowconfigure(i, weight=1)
        for i in range(2):
            parent.grid_columnconfigure(i, weight=1)
    
    def update_timestamp(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"Last Updated: {current_time}")
        self.root.after(1000, self.update_timestamp)
    
    def toggle_connection(self):
        if self.connection and self.connection.is_connected():
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        try:
            self.status_label.config(text="Status: Connecting...", fg='orange')
            self.connect_btn.config(state='disabled')
            self.root.update()
            
            # Try specific port first, then auto-detect
            try:
                self.connection = obd.OBD('/dev/ttyACM0', timeout=30)
                if not self.connection.is_connected():
                    self.connection.close()
                    self.connection = obd.OBD()
            except:
                self.connection = obd.OBD()
            
            if self.connection.is_connected():
                self.status_label.config(text=f"Status: Connected ({self.connection.protocol_name()})", 
                                       fg='green')
                self.connect_btn.config(text="Disconnect", bg='#f44336', state='normal')
                
                # Start data reading thread
                self.is_running = True
                self.data_thread = threading.Thread(target=self.read_data_loop, daemon=True)
                self.data_thread.start()
                
            else:
                self.status_label.config(text="Status: Connection Failed", fg='red')
                self.connect_btn.config(state='normal')
                messagebox.showerror("Connection Error", 
                                   "Failed to connect to OBD-II port.\n\n" +
                                   "Check:\n" +
                                   "• Ignition is ON\n" +
                                   "• OBD adapter is connected\n" +
                                   "• Vehicle is OBD-II compatible")
                
        except Exception as e:
            self.status_label.config(text="Status: Error", fg='red')
            self.connect_btn.config(state='normal')
            messagebox.showerror("Error", f"Connection error: {str(e)}")
    
    def disconnect(self):
        self.is_running = False
        if self.data_thread:
            self.data_thread.join(timeout=2)
        
        if self.connection:
            self.connection.close()
            self.connection = None
        
        self.status_label.config(text="Status: Disconnected", fg='red')
        self.connect_btn.config(text="Connect", bg='#4CAF50', state='normal')
        
        # Reset all values
        for var in self.data_vars.values():
            var.set("--")
    
    def read_data_loop(self):
        # OBD command mappings
        commands = {
            'rpm': obd.commands.RPM,
            'speed': obd.commands.SPEED,
            'coolant_temp': obd.commands.COOLANT_TEMP,
            'throttle_pos': obd.commands.THROTTLE_POS,
            'engine_load': obd.commands.ENGINE_LOAD,
            'intake_temp': obd.commands.INTAKE_TEMP,
            'fuel_level': obd.commands.FUEL_LEVEL,
            'fuel_pressure': obd.commands.FUEL_PRESSURE
        }
        
        while self.is_running and self.connection and self.connection.is_connected():
            try:
                for param, command in commands.items():
                    if not self.is_running:
                        break
                        
                    response = self.connection.query(command)
                    
                    if response.value is not None:
                        # Format the value based on parameter type
                        if param in ['rpm']:
                            value = f"{response.value.magnitude:.0f}"
                        elif param in ['speed']:
                            value = f"{response.value.magnitude:.0f}"
                        elif param in ['coolant_temp', 'intake_temp']:
                            # Show both Celsius and Fahrenheit
                            celsius = response.value.magnitude
                            fahrenheit = celsius * 9/5 + 32
                            value = f"{celsius:.1f}°C\n({fahrenheit:.1f}°F)"
                        else:
                            value = f"{response.value.magnitude:.1f}"
                    else:
                        value = "N/A"
                    
                    # Update GUI in thread-safe way
                    if param in self.data_vars:
                        self.root.after(0, self.data_vars[param].set, value)
                
                time.sleep(0.5)  # Update every 0.5 seconds
                
            except Exception as e:
                print(f"Error reading data: {e}")
                time.sleep(1)
    
    def on_closing(self):
        self.is_running = False
        if self.connection:
            self.connection.close()
        self.root.destroy()

def gui_mode():
    """Run OBD reader in GUI mode"""
    if not GUI_AVAILABLE:
        print("Error: GUI libraries not available.")
        print("Install tkinter or run in terminal mode with: --terminal")
        return
    
    root = tk.Tk()
    app = OBDReaderGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description='OBD-II Data Reader')
    parser.add_argument('--terminal', '-t', action='store_true', 
                       help='Run in terminal mode (default if no display)')
    parser.add_argument('--gui', '-g', action='store_true', 
                       help='Run in GUI mode (default if display available)')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.terminal:
        terminal_mode()
    elif args.gui:
        gui_mode()
    else:
        # Auto-detect best mode
        if GUI_AVAILABLE and os.environ.get('DISPLAY'):
            print("Display detected. Starting GUI mode...")
            print("Use --terminal to force terminal mode")
            gui_mode()
        else:
            print("No display or GUI unavailable. Starting terminal mode...")
            print("Use --gui to force GUI mode")
            terminal_mode()

if __name__ == "__main__":
    main()