import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
import json
import os
from PIL import ImageTk

# Import the backend functions we just built!
import GenAI

# --- Global Variables to hold current album state ---
current_album_data = None
current_cover_image = None
current_tracklist = None


def open_url(url):
    """Opens the given URL in the default web browser."""
    webbrowser.open(url)


def update_ui(album_data, tracklist, cover_img):
    """Updates the Tkinter interface with the new data."""
    global current_album_data, current_cover_image, current_tracklist
    current_album_data = album_data
    current_cover_image = cover_img
    current_tracklist = tracklist

    # 1. Update Album Info text
    info_text = (f"Album: {album_data.get('album_name', 'Unknown')}\n"
                 f"Artist: {album_data.get('artist_name', 'Unknown')}\n"
                 f"Year: {album_data.get('year', 'Unknown')} | Label: {album_data.get('label', 'Unknown')}\n\n"
                 f"Mood: {album_data.get('mood_description', '')}")
    album_info_label.config(text=info_text)

    # 2. Update Cover Image
    if cover_img:

        img_resized = cover_img.resize((300, 300))
        photo = ImageTk.PhotoImage(img_resized)

        # FIX: We must explicitly tell Tkinter to change the width/height to pixels now!
        cover_label.config(image=photo, text="", width=300, height=300)

        cover_label.image = photo  # Keep a reference so it doesn't get garbage collected!
    else:
        cover_label.config(image="", text="[ Image Generation Failed ]", width=50, height=25)

    # 3. Clear existing tracks
    for widget in tracklist_frame.winfo_children():
        widget.destroy()

    # 4. Populate Tracklist
    if tracklist:
        for index, track in enumerate(tracklist):
            track_row = tk.Frame(tracklist_frame, bg="#2b2b2b")
            track_row.pack(fill=tk.X, pady=2)

            # Track Number & Info
            tk.Label(track_row, text=f"{index + 1}. {track['title']} - {track['artist']}",
                     fg="white", bg="#2b2b2b", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

            # Listen Button
            listen_btn = ttk.Button(track_row, text="Listen",
                                    command=lambda u=track['url']: open_url(u))
            listen_btn.pack(side=tk.RIGHT, padx=10)
    else:
        tk.Label(tracklist_frame, text="No tracks found.", fg="white", bg="#2b2b2b").pack()

    status_label.config(text="Status: Generation Complete!", fg="#1DB954")  # Spotify Green
    generate_btn.config(state=tk.NORMAL)


def process_album():
    """Runs in a background thread to fetch data without freezing the GUI."""
    # 1. Get inputs
    mood = mood_text.get('1.0', tk.END).strip()
    genre = genre_var.get()
    era = era_var.get()
    tracks_needed = track_var.get()

    # 2. Fetch Gemini Metadata
    status_label.config(text="Status: Gemini is thinking...", fg="white")
    album_data = GenAI.fetch_gemini_metadata(mood, genre, era)

    if not album_data:
        status_label.config(text="Status: Failed to fetch album concept.", fg="red")
        generate_btn.config(state=tk.NORMAL)
        return

    # 3. Fetch Last.fm Tracks
    status_label.config(text="Status: Fetching real tracks from Last.fm...", fg="white")
    tags = album_data.get("lastfm_tags", [])
    tracklist = GenAI.fetch_tracks(tags, tracks_needed)

    # 4. Generate Cover Image
    status_label.config(text="Status: Painting album cover...", fg="white")
    cover_prompt = album_data.get("cover_prompt", "Abstract music album cover")
    cover_img = GenAI.generate_cover(cover_prompt, genre)

    # 5. Update the UI back on the main thread safely
    root.after(0, update_ui, album_data, tracklist, cover_img)


def start_generation():
    """Triggered by the Generate button."""
    generate_btn.config(state=tk.DISABLED)  # Disable button while working

    # Start the background thread
    thread = threading.Thread(target=process_album)
    thread.daemon = True  # Closes thread if main app is closed
    thread.start()


def save_album():
    """Saves the current album metadata, tracklist, and image to a chosen folder."""
    if not current_album_data or not current_cover_image:
        messagebox.showwarning("Warning", "No album generated yet!")
        return

    folder_path = filedialog.askdirectory(title="Select Folder to Save Album")
    if not folder_path:
        return  # User cancelled

    try:
        # Format the album name to be safe for filenames
        safe_name = "".join([c for c in current_album_data.get('album_name', 'album') if
                             c.isalpha() or c.isdigit() or c == ' ']).rstrip()

        # Save JSON
        json_path = os.path.join(folder_path, f"{safe_name}_data.json")
        export_data = {
            "metadata": current_album_data,
            "tracklist": current_tracklist
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=4, ensure_ascii=False)

        # Save PNG
        img_path = os.path.join(folder_path, f"{safe_name}_cover.png")
        current_cover_image.save(img_path, "PNG")

        messagebox.showinfo("Success", f"Album saved successfully to:\n{folder_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save album:\n{e}")


# --- Main Window Setup ---
root = tk.Tk()
root.title("PDA-226: Album Cover Studio")
# Increased default height so the tracklist still fits under the larger image
root.geometry("1200x850")

# Apply modern theme
style = ttk.Style()
if 'clam' in style.theme_names():
    style.theme_use('clam')

# --- Layout Frames ---
left_frame = tk.Frame(root, padx=20, pady=20, width=350, bg="#001a00")
left_frame.pack(side=tk.LEFT, fill=tk.Y)

right_frame = tk.Frame(root, padx=30, pady=30, bg="#181818")  # Spotify dark background
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# --- Left Panel: Input Widgets ---
genre_var = tk.StringVar(value="Electronic")
era_var = tk.StringVar(value="2000s")
track_var = tk.IntVar(value=10)

tk.Label(left_frame, text="Your Mood/Journal Entry:", font=("Arial", 10, "bold")).pack(anchor="w")
mood_text = tk.Text(left_frame, height=8, width=35, wrap=tk.WORD, bg="#a6a6a6")
mood_text.insert(tk.END,
                 "I was looking at the sea in Izmir. It was raining softly, and an old song was playing through my headphones. I felt both peaceful and melancholic.")
mood_text.pack(pady=(0, 15))

tk.Label(left_frame, text="Genre:").pack(anchor="w")
genre_cb = ttk.Combobox(left_frame, textvariable=genre_var, state="readonly",
                        values=["Pop", "Rock", "Hip-Hop / Rap", "Electronic", "Indie", "R&B / Soul", "Jazz", "Metal",
                                "Türk Pop", "Klasik"])
genre_cb.pack(fill=tk.X, pady=(0, 15))

tk.Label(left_frame, text="Era:").pack(anchor="w")
era_cb = ttk.Combobox(left_frame, textvariable=era_var, state="readonly",
                      values=["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"])
era_cb.pack(fill=tk.X, pady=(0, 15))

tk.Label(left_frame, text="Track Count:").pack(anchor="w")
track_sb = ttk.Spinbox(left_frame, from_=6, to=14, textvariable=track_var, state="readonly")
track_sb.pack(fill=tk.X, pady=(0, 20))

# Style the generate button to look like Spotify green
style.configure("Green.TButton", background="#1DB954", foreground="black", font=("Arial", 10, "bold"))
generate_btn = ttk.Button(left_frame, text="GENERATE ALBUM", command=start_generation, style="Green.TButton")
generate_btn.pack(fill=tk.X, ipady=8)

status_label = tk.Label(left_frame, text="Status: Ready", fg="white", bg="#2b2b2b")
status_label.pack(pady=10)

custom_info_box = tk.Label(left_frame,
                           text="WARNING: All generated albums, artists, year and labels are Fictional",
                           bg="#2b2b2b",   # A slightly different gray to make it look like a "box"
                           fg="white",
                           justify=tk.LEFT,
                           padx=10, pady=10) # Adds some inner spacing so text isn't touching the edge

# packing it to the BOTTOM pushes it as far down the left frame as possible
custom_info_box.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

# --- Right Panel: Output Layout ---
# Top section of right frame (Cover + Info)
header_frame = tk.Frame(right_frame, bg="#181818")
header_frame.pack(fill=tk.X, pady=(0, 20))

# Make the placeholder text box roughly match the new image dimensions
cover_label = tk.Label(header_frame, text="Generated cover will appear here", bg="#282828", fg="gray", width=50,
                       height=25)
cover_label.pack(side=tk.LEFT, padx=(0, 20))

album_info_label = tk.Label(header_frame, text="Describe your mood to generate an album.",
                            bg="#181818", fg="white", justify=tk.LEFT, font=("Arial", 12), wraplength=400)
album_info_label.pack(side=tk.LEFT, anchor="n", pady=10)

# Bottom section of right frame (Tracklist)
tk.Label(right_frame, text="TRACKLIST", bg="#181818", fg="gray", font=("Arial", 10, "bold")).pack(anchor="w")
tracklist_frame = tk.Frame(right_frame, bg="#2b2b2b")
tracklist_frame.pack(fill=tk.BOTH, expand=True, pady=10)

# Save Button at the very bottom
save_btn = ttk.Button(right_frame, text="SAVE ALBUM (JSON + PNG)", command=save_album, style="Green.TButton")
save_btn.pack(fill=tk.X, ipady=5, side=tk.BOTTOM)

# Start the application loop
root.mainloop()