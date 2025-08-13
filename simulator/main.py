import datetime
import socketserver
import customtkinter as ctk
from customtkinter import *
import tkinter as tk
from tkcalendar import Calendar
from core import run_qkd_simulation
import threading
from copy import deepcopy
import math
import json
import webbrowser
import http.server
import os


# Tooltip class for hover descriptions
class ToolTip:
    _current_tooltip = None  # Class variable to track current open tooltip
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Button-1>", self.show_tip)  # Changed to show only
        
    def show_tip(self, event=None):
        # Close any existing tooltip first
        if ToolTip._current_tooltip:
            ToolTip._current_tooltip.hide_tip()
            
        if self.tip_window or not self.text:
            return
            
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(tw, text=self.text, fg_color="#ffffe0", 
                            corner_radius=6, text_color="black")
        label.pack(ipadx=1)
        
        # Bind click events to close on any click
        tw.bind("<Button-1>", lambda e: self.hide_tip())
        
        # Bind to root window for clicks anywhere
        root.bind("<Button-1>", self.check_click_outside)
        
        ToolTip._current_tooltip = self
        
    def check_click_outside(self, event):
        # Check if click was outside the tooltip
        if self.tip_window:
            x, y = event.x_root, event.y_root
            tx, ty = self.tip_window.winfo_x(), self.tip_window.winfo_y()
            tw, th = self.tip_window.winfo_width(), self.tip_window.winfo_height()
            
            if not (tx <= x <= tx + tw and ty <= y <= ty + th):
                self.hide_tip()
        
    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
            ToolTip._current_tooltip = None
            # Unbind the root click event
            root.unbind("<Button-1>")
            
def create_label_with_info(parent, text, tooltip_text):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    
    label = ctk.CTkLabel(frame, text=text)
    label.pack(side="left")  # Using pack inside the frame is fine
    
    if tooltip_text:
        info_icon = ctk.CTkLabel(frame, text="ⓘ", cursor="hand2", font=("Arial", 10))
        info_icon.pack(side="left", padx=(5,0))  # Using pack inside the frame is fine
        ToolTip(info_icon, tooltip_text)
    
    return frame

def set_values_from_config(config):
    for key, value in config.items():
        if key in entries:
            widget = entries[key]
            if key == "date_start":
                try:
                    # Parse the datetime string from config
                    dt = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    # Update calendar widget
                    widget['cal'].selection_set(dt.date())
                    # Update time dropdown
                    time_str = dt.strftime("%H:%M")
                    widget['time_combobox'].set(time_str)
                except ValueError as e:
                    print(f"Error parsing date: {e}")
            elif key == "limit_option":
                entries[key].set(value)
                toggle_limit_options()
            elif isinstance(widget, tuple) and key == "satellite_tle":
                widget[0].delete(0, tk.END)
                widget[0].insert(0, value[0])
                widget[1].delete(0, tk.END)
                widget[1].insert(0, value[1])
            elif isinstance(widget, tk.BooleanVar):
                widget.set(value)
            elif isinstance(widget, tuple):  # Dropdown
                # Find the display value that matches this config value
                display_value = next((k for k,v in widget[1].items() if v == value), None)
                if display_value:
                    widget[0].set(display_value)
            elif hasattr(widget, "delete"):  # Entry field
                widget.delete(0, tk.END)
                widget.insert(0, str(value))

def save_preset():
    config = {}
    for key, widget in entries.items():
        if key == "date_start":
            dt = datetime.datetime.strptime(widget['cal'].get_date(), '%Y-%m-%d')
            time_str = widget['time_combobox'].get()
            config[key] = f"{dt.strftime('%Y-%m-%d')} {time_str}:00"
        elif isinstance(widget, tuple) and key == "satellite_tle":
            config[key] = (widget[0].get(), widget[1].get())
        elif isinstance(widget, tk.BooleanVar):
            config[key] = widget.get()
        elif isinstance(widget, tuple):
            dropdown, mapping = widget
            config[key] = mapping[dropdown.get()]
        elif hasattr(widget, "get"):
            val = widget.get()
            try:
                config[key] = float(val) if '.' in val or 'e' in val.lower() else int(val)
            except ValueError:
                config[key] = val
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=4)

def load_preset():
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file_path:
        with open(file_path, 'r') as f:
            config = json.load(f)
        set_values_from_config(config)

# Friendly names and tooltips
field_info = {
    # Ground Station
    "ground_latitude": ("Ground Station Latitude (°)", "Geographic latitude of the ground station in decimal degrees"),
    "ground_longitude": ("Ground Station Longitude (°)", "Geographic longitude of the ground station in decimal degrees"),
    "ground_altitude": ("Ground Station Altitude (m)", "Height of the ground station above sea level in metres"),
    "receiving_telescope_aperture": ("Receiver Telescope Aperture Diameter (m)", "Diameter of the receiving telescope's primary aperture"),
    "detector_efficiency": ("Detector Photon Efficiency","Percentage of photons arriving at the detector that are successfully converted into detection events"),
    "optical_efficiency": ("Telescope Optical Efficiency","Percentage of photons entering the telescope that reach the detector after passing through the optical system"),
    "detector_maximum_count_rate": ("Detector Maximum Count Rate (MHz)", "Highest photon detection rate the detector can handle without saturation"),
    "dark_count_rate": ("Detector Dark Count Rate (Hz)", "Rate of false photon detections caused by background noise"),

    # Satellite
    "satellite_tle": ("Satellite TLE Data", "Two-Line Element set specifying satellite orbital parameters"),
    "sending_telescope_aperture": ("Transmitter Telescope Aperture Diameter (m)", "Diameter of the transmitting telescope's primary aperture"),
    "beam_divergence": ("Beam Divergence (rad)", "Full angular spread of the transmitted beam in radians"),
    "point_acc_min": ("Pointing Accuracy - Best Case (µrad)", "Smallest achievable pointing error of the acquisition, pointing, and tracking (APT) system"),
    "point_acc_max": ("Pointing Accuracy - Worst Case (µrad)", "Largest possible pointing error of the APT system"),
    "weak_coherent_pulse_rate": ("Pulse Emission Rate (MHz)", "Rate of emitted weak coherent pulses or single-photon states (depending on protocol)"),

    # Channel
    "uplink_bandwidth": ("Uplink Bandwidth (Mbit/s)", "Maximum data transmission rate for the uplink classical channel"),
    "downlink_bandwidth": ("Downlink Bandwidth (Mbit/s)", "Maximum data transmission rate for the downlink classical channel"),
    "min_elevation_angle_start": ("Minimum Start Elevation Angle (°)", "Minimum satellite elevation angle above the horizon to begin communication"),
    "min_elevation_angle_end": ("Minimum End Elevation Angle (°)", "Minimum satellite elevation angle above the horizon to end communication"),

    # Quantum
    "photon_wavelength": ("Photon Wavelength (nm)", "Wavelength of transmitted photons in nanometres"),
    "signal_mean_photon_num": ("Mean Photon Number - Signal State", "Average number of photons per pulse for the signal state"),
    "decoy_mean_photon_num": ("Mean Photon Number - Decoy State", "Average number of photons per pulse for the decoy state"),
    "signal_prob": ("Signal State Probability", "Probability of sending a signal state in the QKD protocol"),
    "decoy_prob": ("Decoy State Probability", "Probability of sending a decoy state in the QKD protocol"),
    "time_window": ("Detector Time Window (ns)", "Time duration during which the detector is active for each detection event"),
    "depolarization_error": ("Depolarization Error Rate", "Fraction of photons that undergo polarization changes during transmission"),
    "percentage_estimate_qber": ("QBER Estimation Fraction (%)", "Fraction of the raw key used to estimate the Quantum Bit Error Rate"),

    # Time
    "date_start": ("Simulation Start Date & Time", "Start time for the simulation, aligned to the nearest valid satellite pass"),
    "qkd_time": ("Effective QKD Usage (%)", "Percentage of satellite pass time effectively used for quantum key distribution"),
    "max_range": ("Maximum Slant Range (km)", "Only simulate when satellite slant range is below this threshold distance"),

    # Environment
    "weather_auto": ("Automatic Weather Selection", "Automatically determine weather conditions based on location and time"),
    "climate_model": ("Atmospheric Climate Model", "1 - Tropical, 2 - Midlatitude Summer, 3 - Midlatitude Winter, 4 - Subarctic Summer, 5 - Subarctic Winter, 6 - US Standard"),
    "precipitable_water": ("Precipitable Water Vapour (mm)", "Total column water vapour in the atmosphere in millimetres"),
    "ozone_depth": ("Ozone Column Depth (DU)", "Total atmospheric ozone amount in Dobson Units"),
    "ground_pressure": ("Ground-Level Atmospheric Pressure (hPa)", "Atmospheric pressure measured at ground station altitude"),
    "aerosol_depth": ("Aerosol Optical Depth (550 nm)", "Vertical optical depth due to aerosols at a wavelength of 550 nm"),
    "cloud_depth": ("Cloud Optical Depth", "Vertical optical thickness of clouds in the atmosphere"),
    
    # Protocol & Post-Processing
    "qkd_protocol": ("QKD Protocol Selection", "Quantum key distribution protocol to use for the simulation"),
    "two_universal": ("Two-Universal Hash Function", "Chosen two-universal hash function for privacy amplification"),
    "cascade": ("Cascade Error Correction Variant", "Selected variant of the Cascade protocol for error correction")
}


default_config = {key: "" for key in field_info.keys()}
default_config["weather_auto"] = True
default_config["satellite_tle"] = ("", "")

config_template = deepcopy(default_config)

ctk.set_appearance_mode("dark")  

# Tkinter GUI
root = ctk.CTk()
root.title("OpenSATQKD")
root.geometry("1000x800")

# Create main container frames
root.grid_rowconfigure(0, weight=2)  # 2/3 for inputs
root.grid_rowconfigure(1, weight=1)  # 1/3 for output
root.grid_columnconfigure(0, weight=1)

upper_frame = ctk.CTkFrame(root)
upper_frame.grid(row=0, column=0, sticky="nsew")

lower_frame = ctk.CTkFrame(root)
lower_frame.grid(row=1, column=0, sticky="nsew")

scrollable_frame = ctk.CTkScrollableFrame(upper_frame)
scrollable_frame.pack(fill="both", expand=True)

entries = {}
row = 0

# Section titles
sections = {
    "Ground Station": [
        "ground_latitude", "ground_longitude", "ground_altitude",
        "receiving_telescope_aperture", "optical_efficiency", "detector_efficiency",
        "detector_maximum_count_rate", "dark_count_rate"
    ],
    "Satellite": [
        "satellite_tle",
        "sending_telescope_aperture", "beam_divergence", "weak_coherent_pulse_rate",
        "point_acc_min", "point_acc_max"
    ],
    "Communication Link": [
        "uplink_bandwidth", "downlink_bandwidth",
        "min_elevation_angle_start", "min_elevation_angle_end"
    ],
    "Quantum Signal Parameters": [
        "photon_wavelength", "signal_mean_photon_num", "decoy_mean_photon_num",
        "signal_prob", "decoy_prob",
        "time_window", "depolarization_error", "percentage_estimate_qber",
        "qkd_protocol"
    ],
    "Simulation Control": [
        "date_start", "limit_option", "qkd_time", "max_range", "two_universal", "cascade"
    ],
    "Environment": [
        "cloud_depth", "precipitable_water", "ozone_depth", "ground_pressure",
        "aerosol_depth", "weather_auto", "climate_model"
    ]
}

active_limit_option = tk.StringVar(value="max_range")

def make_dropdown(key, display_options):
    # Automatically create mapping from displayed value → config value
    value_map = {opt: opt.replace(' ', '_').lower() for opt in display_options}
    combobox = ctk.CTkOptionMenu(scrollable_frame, values=display_options)
    combobox.set(display_options[0])  
    combobox.grid(row=row, column=1)
    entries[key] = (combobox, value_map)
    return combobox

def create_start_time_picker(parent_frame, tooltip_text):
    # Create a frame for the start time input
    start_time_frame = ctk.CTkFrame(parent_frame)
    start_time_frame.grid(row=row, column=1, pady=(10, 10), sticky=tk.W)

    # Add Calendar widget for date
    cal = Calendar(start_time_frame, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.grid(row=0, column=0, padx=(5, 10))

    # Add Time Combobox (HH:MM format)
    time_options = [f"{hour:02}:{minute:02}" for hour in range(24) for minute in range(0, 60, 15)]
    time_combobox = ctk.CTkOptionMenu(start_time_frame, values=time_options)
    time_combobox.set("12:00")  # Default time
    time_combobox.grid(row=0, column=1, padx=(10, 5))

    # Combine date and time into desired format
    def get_datetime():
        date = cal.get_date()
        time = time_combobox.get()
        start_datetime = f"{date} {time}:00"
        datetime_obj = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        return datetime_obj

    return start_time_frame, get_datetime

def get_theme_colors():
    """Returns color settings based on current theme"""
    if ctk.get_appearance_mode() == "Dark":
        return {
            "disabled_bg": "#3a3a3a",
            "disabled_fg": "#707070",
            "normal_label": "#ffffff",
            "enabled_bg": "#343638",
            "enabled_fg": "#dce4ee",
            "border_color": "#565b5e",
            "dropdown_enabled_fg": "#1F6AA5",
            "dropdown_button_color": "#274472"
        }
    else:
        return {
            "disabled_bg": "#e0e0e0",
            "disabled_fg": "#909090",
            "normal_label": "#000000",
            "enabled_bg": "#f9f9f9",
            "enabled_fg": "#000000",
            "border_color": "#d9d9d9",
            "dropdown_enabled_fg": "#1F6AA5",
            "dropdown_button_color": "#274472"
        }

def configure_widget_state(widget, enabled, colors):
    """Configures widget appearance based on enabled state"""
    if isinstance(widget, tuple):  # Dropdowns
        dropdown = widget[0]
        if enabled:
            dropdown.configure(state="normal",
                            fg_color=colors["dropdown_enabled_fg"],
                            text_color=colors["enabled_fg"],
                            button_color=colors["dropdown_button_color"])
        else:
            dropdown.configure(state="disabled",
                            fg_color=colors["disabled_bg"],
                            text_color=colors["disabled_fg"],
                            button_color=colors["disabled_bg"])
    else:  # Regular entries
        if enabled:
            widget.configure(state="normal",
                           fg_color=colors["enabled_bg"],
                           text_color=colors["enabled_fg"],
                           border_color=colors["border_color"])
        else:
            widget.configure(state="disabled",
                           fg_color=colors["disabled_bg"],
                           text_color=colors["disabled_fg"],
                           border_color=colors["disabled_bg"])

def toggle_weather_dependent_fields():
    """Toggle weather-dependent fields based on auto weather checkbox"""
    weather_auto = entries["weather_auto"].get()
    colors = get_theme_colors()
    
    # Field configuration
    manual_weather_fields = {
        "climate_model": entries["climate_model"],
        "precipitable_water": entries["precipitable_water"],
        "ozone_depth": entries["ozone_depth"],
        "ground_pressure": entries["ground_pressure"],
        "aerosol_depth": entries["aerosol_depth"],
    }
    
    label_mapping = {
        "Climate Model": "climate_model",
        "Precipitable Water Vapor (mm)": "precipitable_water",
        "Ozone Column Depth (DU)": "ozone_depth",
        "Ground Pressure (hPa)": "ground_pressure",
        "Aerosol Depth": "aerosol_depth",
    }
    
    # Update widgets and labels
    for label_text, field_key in label_mapping.items():
        # Find and configure the label
        label = find_label_by_text(label_text)
        if label:
            label.configure(text_color=colors["normal_label"] if not weather_auto else colors["disabled_fg"])
        
        # Configure the associated widget
        if field_key in manual_weather_fields:
            configure_widget_state(manual_weather_fields[field_key], not weather_auto, colors)

def find_label_by_text(text):
    """Helper to find a label by its text content"""
    for child in scrollable_frame.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            for subchild in child.winfo_children():
                if isinstance(subchild, ctk.CTkLabel) and subchild.cget("text") == text:
                    return subchild
    return None
                
def toggle_limit_options():
    """Toggle between qkd_time and max_range options"""
    option = active_limit_option.get()
    colors = get_theme_colors()
    
    # Field configuration
    limit_fields = {
        "qkd_time": {
            "widget": entries["qkd_time"],
            "label_text": "Effective QKD Time"
        },
        "max_range": {
            "widget": entries["max_range"],
            "label_text": "Maximum Slant Range (km)"
        }
    }
    
    # Update widgets and labels
    for field_key, field_data in limit_fields.items():
        is_enabled = (option == field_key)
        widget = field_data["widget"]
        label_text = field_data["label_text"]
        
        # Configure the widget
        configure_widget_state(widget, is_enabled, colors)
        
        # Configure the label
        label = find_label_by_text(label_text)
        if label:
            label.configure(text_color=colors["normal_label"] if is_enabled else colors["disabled_fg"])


for section, keys in sections.items():
    header = ctk.CTkLabel(scrollable_frame, text=section, font=("Arial", 12, "bold"))
    header.grid(row=row, column=0, columnspan=2, pady=(10, 5), sticky=tk.W)
    row += 1

    for key in keys:
        if key == "date_start":  # When handling the start_time field
            label_frame = create_label_with_info(scrollable_frame, "Start Time", field_info[key][1])
            label_frame.grid(row=row, column=0, sticky=tk.W)
            
            start_time_frame, get_start_time = create_start_time_picker(
                scrollable_frame, 
                field_info[key][1]
            )
            
            # Store both the frame and getter function
            entries[key] = {
                'frame': start_time_frame,
                'getter': get_start_time,
                'cal': start_time_frame.children['!calendar'],
                'time_combobox': start_time_frame.children['!ctkoptionmenu']
            }
            row += 1
            
        elif key == "satellite_tle":
            # For TLE Line 1
            label_frame = create_label_with_info(scrollable_frame, "TLE Line 1", field_info[key][1])
            label_frame.grid(row=row, column=0, sticky=tk.W)
            entry1 = ctk.CTkEntry(scrollable_frame, width=500)
            entry1.insert(0, config_template[key][0])
            entry1.grid(row=row, column=1)
            row += 1

            # For TLE Line 2
            label_frame = create_label_with_info(scrollable_frame, "TLE Line 2", field_info[key][1])
            label_frame.grid(row=row, column=0, sticky=tk.W)
            entry2 = ctk.CTkEntry(scrollable_frame, width=500)
            entry2.insert(0, config_template[key][1])
            entry2.grid(row=row, column=1)
            entries[key] = (entry1, entry2)
            row += 1
        elif key == "weather_auto":
            var = tk.BooleanVar(value=config_template[key])
            cb = ctk.CTkCheckBox(scrollable_frame, 
                    text=field_info[key][0], 
                    variable=var,
                    command=toggle_weather_dependent_fields)
            cb.grid(row=row, column=0, columnspan=2, sticky=tk.W)
            help_label = ctk.CTkLabel(scrollable_frame, 
                                    text="(uses automatic weather based on location and time when checked)",
                                    text_color="#808080",
                                    font=("Arial", 10))
            help_label.grid(row=row, column=1, sticky=tk.W, padx=(10,0))
            entries[key] = var
            row += 1
        elif key == "limit_option":
            # Radio buttons for choosing which limit to use
            label_frame = create_label_with_info(scrollable_frame, "Limit By:", "Choose whether to limit by time percentage or maximum range")
            label_frame.grid(row=row, column=0, sticky=tk.W)
            
            radio_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            radio_frame.grid(row=row, column=1, sticky=tk.W)
            
            time_radio = ctk.CTkRadioButton(
                radio_frame, 
                text="QKD Time %", 
                variable=active_limit_option, 
                value="qkd_time",
                command=toggle_limit_options
            )
            time_radio.pack(side="left", padx=5)
            
            range_radio = ctk.CTkRadioButton(
                radio_frame, 
                text="Max Range", 
                variable=active_limit_option, 
                value="max_range",
                command=toggle_limit_options
            )
            range_radio.pack(side="left", padx=5)
            entries[key]=active_limit_option
            row += 1
        else:
            label_text, tooltip = field_info[key]
            label_frame = create_label_with_info(scrollable_frame, label_text, tooltip)
            label_frame.grid(row=row, column=0, sticky=tk.W)

            # Dropdown options for specific fields
            if key == "climate_model":
                climate_map = {
                    "Tropical": "tp", "Midlatitude Summer": "ms", "Midlatitude Winter": "mw",
                    "Subarctic Summer": "ss", "Subarctic Winter": "sw", "US Standard": "us"
                }
                combobox = ctk.CTkOptionMenu(scrollable_frame, values=list(climate_map.keys()))
                combobox.set("Tropical")
                combobox.grid(row=row, column=1)
                entries[key] = (combobox, climate_map)
            elif key in ["qkd_protocol", "two_universal", "cascade"]:
                options = {
                    "qkd_protocol": ["Decoy_State", "BB84"],
                    "two_universal": ["Toeplitz", "Circulant"],
                    "cascade": ["Original", "Biconf", "Yanetal"]
                }
                make_dropdown(key, options[key])
            else:
                entry = ctk.CTkEntry(scrollable_frame, width=100)
                entry.insert(0, config_template[key])
                entry.grid(row=row, column=1)
                entries[key] = entry

            row += 1

toggle_weather_dependent_fields()  
toggle_limit_options()

# Output box in bottom section
output_box = ctk.CTkTextbox(lower_frame, wrap="word")
output_box.pack(side="left", fill="both", expand=True)

def validate_inputs(config):
    """Validate all input parameters and return error messages if any are invalid"""
    errors = []
    
    # Helper function to check if value is within range
    def check_range(name, value, min_val, max_val):
        # Handle infinite bounds
        lower_ok = (min_val == -math.inf) or (value >= min_val)
        upper_ok = (max_val == math.inf) or (value <= max_val)
        
        if not (lower_ok and upper_ok):
            # Format the range display nicely for infinite bounds
            range_str = ""
            if min_val == -math.inf and max_val == math.inf:
                range_str = "any value"
            elif min_val == -math.inf:
                range_str = f"≤ {max_val}"
            elif max_val == math.inf:
                range_str = f"≥ {min_val}"
            else:
                range_str = f"between {min_val} and {max_val}"
                
            errors.append(f"{field_info[name][0]} must be {range_str}")
    
    # Validate numeric fields - using +/- inf where appropriate
    numeric_fields = {
        "ground_latitude": (-90, 90),  # Fixed bounds
        "ground_longitude": (-180, 180),  # Fixed bounds
        "ground_altitude": (0, math.inf),  # Must be ≥ 0
        "receiving_telescope_aperture": (0.0001, math.inf),
        "detector_efficiency": (0, 1),  # Percentage (0-1)
        "optical_efficiency": (0, 1),
        "detector_maximum_count_rate": (0.0001, math.inf),
        "dark_count_rate": (0, math.inf),
        "sending_telescope_aperture": (0.0001, math.inf),
        "beam_divergence": (0.000000001, math.inf),
        "point_acc_min": (0.000000001, math.inf),
        "point_acc_max": (0.000000001, math.inf),
        "weak_coherent_pulse_rate": (0.0001, math.inf),
        "uplink_bandwidth": (0.0001, math.inf),
        "downlink_bandwidth": (0.0001, math.inf),
        "min_elevation_angle_start": (0, 90),  # Degrees (0-90)
        "min_elevation_angle_end": (0, 90),
        "photon_wavelength": (30, 20000),  # Nanometers (typical optical range)
        "signal_mean_photon_num": (0, 1),  # Photon number (0-1)
        "decoy_mean_photon_num": (0, 1),  # Photon number (0-1)
        "signal_prob": (0, 1),  # Probability (0-1)
        "decoy_prob": (0, 1),  # Probability (0-1)
        "time_window": (0.0001, math.inf),
        "depolarization_error": (0, 1),  # Error rate (0-1)
        "percentage_estimate_qber": (0, 1),  # Percentage (0-1)
        "precipitable_water": (0, math.inf),  # mm 
        "ozone_depth": (0, math.inf),  # Dobson units 
        "ground_pressure": (0, math.inf),  # hPa 
        "aerosol_depth": (0, math.inf), 
        "cloud_depth": (0, math.inf), 
        "qkd_time": (0, 1),
        "max_range": (0, math.inf),
    }

    active_limit = active_limit_option.get()
    if active_limit == "qkd_time":
        numeric_fields.pop("max_range", None)
    else:
        numeric_fields.pop("qkd_time", None)
    
    for field, (min_val, max_val) in numeric_fields.items():
        if config["weather_auto"] and field in ["precipitable_water", "ozone_depth", "ground_pressure", "aerosol_depth"]:
            continue
        try:
            value = float(config[field])
            check_range(field, value, min_val, max_val)
        except ValueError:
            errors.append(f"{field_info[field][0]} must be a valid number")
    
    # Special validations
    if config["signal_prob"] + config["decoy_prob"] > 1:
        errors.append("Sum of signal and decoy probabilities cannot exceed 1")

    if config["point_acc_min"] > config["point_acc_max"]:
        errors.append("Worst case pointing accuracy must be smaller than best case")
    
    # Validate TLE format (now always required)
    tle1, tle2 = config["satellite_tle"]
    if len(tle1) < 10 or len(tle2) < 10:
        errors.append("Invalid TLE format - both lines must be provided")
    
    return errors

def show_error_dialog(errors):
    """Show a popup with validation errors"""
    error_window = ctk.CTkToplevel(root)
    error_window.title("Input Validation Errors")
    error_window.geometry("500x300")
    
    scroll_frame = ctk.CTkScrollableFrame(error_window)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    error_label = ctk.CTkLabel(scroll_frame, 
                             text="Please fix the following errors:",
                             font=("Arial", 12, "bold"))
    error_label.pack(anchor="w", pady=(0, 10))
    
    for error in errors:
        item = ctk.CTkLabel(scroll_frame, text=f"• {error}", anchor="w")
        item.pack(fill="x", padx=5, pady=2)
    
    ok_button = ctk.CTkButton(error_window, 
                            text="OK", 
                            command=error_window.destroy)
    ok_button.pack(pady=10)

def run_simulation():
    # First collect all inputs
    config = {}
    for key, widget in entries.items():
        if key == "date_start":
            dt = datetime.datetime.strptime(widget['cal'].get_date(), '%Y-%m-%d')
            time_str = widget['time_combobox'].get()
            config[key] = f"{dt.strftime('%d/%m/%Y')} {time_str}:00"
        elif isinstance(widget, tuple) and key == "satellite_tle":
            config[key] = (widget[0].get(), widget[1].get())
        elif isinstance(widget, tk.BooleanVar):
            config[key] = widget.get()
        elif isinstance(widget, tuple):
            dropdown, mapping = widget
            config[key] = mapping[dropdown.get()]
        elif hasattr(widget, "get"):
            val = widget.get()
            try:
                # Try to convert to float if it looks like a number
                config[key] = float(val) if '.' in val or 'e' in val.lower() else int(val)
            except ValueError:
                config[key] = val

    # Validate inputs before proceeding
    errors = validate_inputs(config)
    if errors:
        show_error_dialog(errors)
        return
    
    # If validation passed, proceed with simulation
    run_button.configure(state=tk.DISABLED)
    output_box.delete(1.0, tk.END)
    output_box.insert(tk.END, "Running simulation...\n")
    
    def task():
        try:
            result_generator = run_qkd_simulation(config)
            for result in result_generator:
                if isinstance(result, tuple) and result[0] == "sat_coords":
                    _, satlat, satlon, elevation, ranges, photons = result
                    show_satellite_map_with_animation(
                        satlat, satlon, elevation, ranges,
                        config["ground_latitude"], config["ground_longitude"], photons
                    )
                elif isinstance(result, str):
                    output_box.insert(tk.END, result + "\n")
                    output_box.yview(tk.END)
                    root.update_idletasks()
        except Exception as e:
            output_box.insert(tk.END, f"Error: {str(e)}\n")
        finally:
            run_button.configure(state=tk.NORMAL)

    threading.Thread(target=task, daemon=True).start()

preset_frame = ctk.CTkFrame(upper_frame)
preset_frame.pack(pady=5)

save_button = ctk.CTkButton(preset_frame, text="Save Preset", command=save_preset)
save_button.pack(side="left", padx=5)

load_button = ctk.CTkButton(preset_frame, text="Load Preset", command=load_preset)
load_button.pack(side="left", padx=5)

# Run button
run_button = ctk.CTkButton(upper_frame, text="Run Simulation", command=run_simulation)
run_button.pack(pady=5)

def show_satellite_map_with_animation(satlat, satlon, elevation, ranges, ground_lat, ground_lon, photons):
    """Display satellite animation on a map"""
    try:
        # Convert all NumPy arrays to lists
        latlngs = list(zip(satlat.tolist(), satlon.tolist()))
        elevations = elevation.tolist()
        ranges = ranges.tolist()

        # Create HTML with animation
        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Satellite Animation</title>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    #controls {{
                        position: absolute;
                        top: 10px;
                        left: 50%;
                        transform: translateX(-50%);
                        z-index: 1000;
                        background: rgba(255,255,255,0.8);
                        padding: 10px;
                        border-radius: 8px;
                        box-shadow: 0 0 5px rgba(0,0,0,0.3);
                    }}
                    #slider {{
                        width: 300px;
                    }}
                </style>
            </head>
            <body>
                <div id="controls">
                    <button onclick="play()">▶ Play</button>
                    <button onclick="pause()">⏸ Pause</button>
                    <input type="range" id="slider" min="0" max="{len(latlngs) - 1}" value="0" />
                </div>
                <div id="map" style="width: 100%; height: 100vh;"></div>
                <script>
                    var map = L.map('map').setView([{ground_lat}, {ground_lon}], 5);

                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        attribution: 'Map data © OpenStreetMap contributors'
                    }}).addTo(map);

                    // Ground station
                    L.marker([{ground_lat}, {ground_lon}], {{icon: L.icon({{
                        iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/d/d5/P_satellite_dish.svg',
                        iconSize: [32, 32]
                    }})}}).addTo(map).bindPopup('Ground Station');

                    var latlngs = {json.dumps(latlngs)};
                    var elevations = {json.dumps(elevations)};
                    var ranges = {json.dumps(ranges)};
                    var photons = {json.dumps(photons.tolist())};
                    var satIcon = L.icon({{
                        iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/1/1b/Satellite_of_GDAL.svg',
                        iconSize: [32, 32]
                    }});
                    var marker = L.marker(latlngs[0], {{icon: satIcon}}).addTo(map);
                    var polyline = L.polyline(latlngs, {{color: 'red'}}).addTo(map);

                    var i = 0;
                    var interval = null;

                    function updateMarker(index) {{
                        marker.setLatLng(latlngs[index]);
                        marker.bindPopup("Elevation: " + elevations[index].toFixed(2) + "°<br>Range: " + ranges[index].toFixed(2) + " km<br>" +
        "Photons: " + parseInt(photons[index]).toLocaleString()).openPopup();
                        document.getElementById("slider").value = index;
                    }}

                    function play() {{
                        if (interval) return;
                        interval = setInterval(() => {{
                            if (i >= latlngs.length) {{
                                clearInterval(interval);
                                interval = null;
                                return;
                            }}
                            updateMarker(i);
                            i++;
                        }}, 1000);
                    }}

                    function pause() {{
                        clearInterval(interval);
                        interval = null;
                    }}

                    document.getElementById("slider").addEventListener("input", function(e) {{
                        i = parseInt(e.target.value);
                        updateMarker(i);
                    }});

                    updateMarker(0);
                </script>
            </body>
            </html>
            """

        # Write the HTML to ~/Documents/satellite_animation/index.html
        output_dir = os.path.expanduser("~/Documents/satellite_animation")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "index.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        # Start a simple HTTP server
        PORT = 8000

        def serve_once():
            os.chdir(output_dir)
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", PORT), handler) as httpd:
                httpd.timeout = 10  # Optional: stops waiting if no request comes in
                print(f"Serving once at http://localhost:{PORT}")
                httpd.handle_request()  # Serve a single request and exit

        threading.Thread(target=serve_once, daemon=True).start()
        webbrowser.open(f"http://localhost:{PORT}")

    except Exception as e:
        print(f"Map generation failed: {e}")

if __name__ == "__main__":
    root.mainloop()