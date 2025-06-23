# geocode_excel_gui.py

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import os
import threading # Pour exécuter le géocodage en arrière-plan et ne pas figer l'GUI

# --- La fonction de géocodage reste similaire ---
def geocode_dataframe_threaded(df, address_cols, lat_col_name, lon_col_name, user_agent, text_area_log, progress_callback):
    """
    Fonction de géocodage adaptée pour être lancée dans un thread et logger dans une Text Area.
    """
    try:
        log_message(text_area_log, f"Initialisation du géocodeur avec User-Agent: {user_agent}")
        geolocator = Nominatim(user_agent=user_agent)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1, return_value_on_exception=None, max_retries=2)

        df[lat_col_name] = None
        df[lon_col_name] = None

        total_rows = len(df)
        log_message(text_area_log, f"Début du géocodage pour {total_rows} lignes...")
        progress_callback(0, total_rows) # Mise à jour initiale de la progression

        for index, row in df.iterrows():
            address_parts = [str(row[col]) for col in address_cols if pd.notna(row[col]) and str(row[col]).strip()]
            address = ", ".join(address_parts)

            if not address:
                log_message(text_area_log, f"Ligne {index + 2}/{total_rows}: Adresse vide, ignoré.")
                progress_callback(index + 1, total_rows)
                continue

            log_message(text_area_log, f"Ligne {index + 2}/{total_rows}: Géocodage de '{address}'...")
            
            location = None
            try:
                location = geocode(address, timeout=10, language='en')
            except Exception as e:
                log_message(text_area_log, f"  -> Erreur: {e}")
                continue

            if location:
                df.loc[index, lat_col_name] = location.latitude
                df.loc[index, lon_col_name] = location.longitude
                log_message(text_area_log, f"  -> Trouvé: Lat: {location.latitude:.4f}, Lon: {location.longitude:.4f}")
            else:
                log_message(text_area_log, f"  -> Non trouvé pour '{address}'.")
                df.loc[index, lat_col_name] = "Non trouvé"
                df.loc[index, lon_col_name] = "Non trouvé"
            
            progress_callback(index + 1, total_rows) # Mettre à jour la progression

        log_message(text_area_log, "Géocodage terminé.")
        return df
    except Exception as e:
        log_message(text_area_log, f"ERREUR CRITIQUE DANS LE THREAD DE GEOCODAGE: {e}")
        return None # Indiquer une erreur

def log_message(text_area, message):
    """Ajoute un message à la Text Area de log, en s'assurant que c'est thread-safe."""
    text_area.insert(tk.END, message + "\n")
    text_area.see(tk.END) # Auto-scroll
    text_area.update_idletasks() # Forcer la mise à jour de l'UI

# --- Classe principale de l'application GUI ---
class GeocoderApp:
    def __init__(self, master):
        self.master = master
        master.title("Outil de Géocodage Excel")
        master.geometry("700x550") # Taille de la fenêtre

        # Variables Tkinter
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.user_agent_var = tk.StringVar(value="MonAppGeocodageEntreprise/1.0 (contact@entreprise.com)") # Valeur par défaut
        self.addr_col_promoter_var = tk.StringVar(value="Nom Lieu / Promoter")
        self.addr_col_city_var = tk.StringVar(value="Ville")
        self.addr_col_country_var = tk.StringVar(value="Pays")
        self.lat_output_col_var = tk.StringVar(value="Latitude_Geocodee")
        self.lon_output_col_var = tk.StringVar(value="Longitude_Geocodee")

        # --- Widgets ---
        # Frame pour la sélection de fichier
        file_frame = tk.LabelFrame(master, text="Fichier Excel", padx=10, pady=10)
        file_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(file_frame, text="Fichier d'entrée:").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(file_frame, textvariable=self.input_file_path, width=60, state="readonly").grid(row=0, column=1, padx=5, pady=2)
        tk.Button(file_frame, text="Parcourir...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=2)

        tk.Label(file_frame, text="Fichier de sortie:").grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(file_frame, textvariable=self.output_file_path, width=60, state="readonly").grid(row=1, column=1, padx=5, pady=2)


        # Frame pour les configurations
        config_frame = tk.LabelFrame(master, text="Configuration", padx=10, pady=10)
        config_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(config_frame, text="User-Agent (Nominatim):").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(config_frame, textvariable=self.user_agent_var, width=50).grid(row=0, column=1, padx=5, pady=2, columnspan=2)
        
        # Section avancée pour les noms de colonnes (pourrait être cachée par défaut)
        tk.Label(config_frame, text="--- Noms des colonnes (avancé) ---").grid(row=1, column=0, columnspan=3, pady=5)
        tk.Label(config_frame, text="Col. Nom Lieu/Promoter:").grid(row=2, column=0, sticky="w", pady=2)
        tk.Entry(config_frame, textvariable=self.addr_col_promoter_var, width=25).grid(row=2, column=1, padx=5, pady=2)
        tk.Label(config_frame, text="Col. Ville:").grid(row=3, column=0, sticky="w", pady=2)
        tk.Entry(config_frame, textvariable=self.addr_col_city_var, width=25).grid(row=3, column=1, padx=5, pady=2)
        tk.Label(config_frame, text="Col. Pays:").grid(row=4, column=0, sticky="w", pady=2)
        tk.Entry(config_frame, textvariable=self.addr_col_country_var, width=25).grid(row=4, column=1, padx=5, pady=2)

        tk.Label(config_frame, text="Col. Sortie Latitude:").grid(row=2, column=2, sticky="w", padx=10, pady=2)
        tk.Entry(config_frame, textvariable=self.lat_output_col_var, width=25).grid(row=2, column=3, padx=5, pady=2)
        tk.Label(config_frame, text="Col. Sortie Longitude:").grid(row=3, column=2, sticky="w", padx=10, pady=2)
        tk.Entry(config_frame, textvariable=self.lon_output_col_var, width=25).grid(row=3, column=3, padx=5, pady=2)


        # Bouton Lancer
        self.run_button = tk.Button(master, text="Lancer le Géocodage", command=self.start_geocoding_thread, font=("Arial", 12, "bold"), bg="green", fg="white")
        self.run_button.pack(pady=10)

        # Zone de Log
        log_frame = tk.LabelFrame(master, text="Journal des opérations", padx=10, pady=10)
        log_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        # Barre de progression (simple label pour l'instant)
        self.progress_label = tk.Label(master, text="Progression: 0/0")
        self.progress_label.pack(pady=5)


    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=(("Fichiers Excel", "*.xlsx *.xls"), ("Tous les fichiers", "*.*"))
        )
        if filename:
            self.input_file_path.set(filename)
            base, ext = os.path.splitext(filename)
            self.output_file_path.set(f"{base}_geocode{ext}")
            log_message(self.log_text_enabled(), f"Fichier d'entrée sélectionné: {filename}")
            log_message(self.log_text_enabled(), f"Fichier de sortie sera: {self.output_file_path.get()}")

    def log_text_enabled(self):
        """Active la Text Area pour l'écriture, puis la désactive."""
        self.log_text.config(state="normal")
        # Pas besoin de la retourner directement si log_message le fait, mais pratique pour le contexte
        return self.log_text

    def update_progress(self, current, total):
        if total > 0:
            percentage = (current / total) * 100
            self.progress_label.config(text=f"Progression: {current}/{total} ({percentage:.1f}%)")
        else:
            self.progress_label.config(text="Progression: 0/0")
        self.master.update_idletasks() # Forcer la mise à jour de l'UI

    def start_geocoding_thread(self):
        input_file = self.input_file_path.get()
        output_file = self.output_file_path.get()
        user_agent = self.user_agent_var.get()
        
        addr_cols = []
        if self.addr_col_promoter_var.get(): addr_cols.append(self.addr_col_promoter_var.get())
        if self.addr_col_city_var.get(): addr_cols.append(self.addr_col_city_var.get())
        if self.addr_col_country_var.get(): addr_cols.append(self.addr_col_country_var.get())

        lat_out_col = self.lat_output_col_var.get()
        lon_out_col = self.lon_output_col_var.get()

        if not input_file:
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier Excel d'entrée.")
            return
        if not user_agent:
            messagebox.showerror("Erreur", "Veuillez spécifier un User-Agent pour Nominatim.")
            return
        if not addr_cols:
            messagebox.showerror("Erreur", "Veuillez spécifier au moins une colonne pour construire l'adresse.")
            return
        if not lat_out_col or not lon_out_col:
            messagebox.showerror("Erreur", "Veuillez spécifier les noms des colonnes de sortie pour la latitude et la longitude.")
            return

        self.run_button.config(state="disabled", text="Géocodage en cours...")
        log_area = self.log_text_enabled() # Récupérer la text area activée
        
        # Lancer le géocodage dans un thread séparé
        thread = threading.Thread(target=self.run_geocoding_process, 
                                  args=(input_file, output_file, addr_cols, lat_out_col, lon_out_col, user_agent, log_area))
        thread.daemon = True # Permet à l'application de se fermer même si le thread tourne
        thread.start()

    def run_geocoding_process(self, input_file, output_file, addr_cols, lat_out_col, lon_out_col, user_agent, log_area_ref):
        try:
            log_message(log_area_ref, f"Lecture du fichier Excel: {input_file}")
            df_entree = pd.read_excel(input_file, engine='openpyxl')

            if df_entree.empty:
                log_message(log_area_ref, "Le fichier Excel est vide. Arrêt.")
                self.run_button.config(state="normal", text="Lancer le Géocodage")
                return

            missing_address_cols = [col for col in addr_cols if col not in df_entree.columns]
            if missing_address_cols:
                msg = f"ERREUR: Colonnes d'adresse manquantes: {', '.join(missing_address_cols)}"
                log_message(log_area_ref, msg)
                messagebox.showerror("Erreur de colonnes", msg)
                self.run_button.config(state="normal", text="Lancer le Géocodage")
                return

            df_sortie = geocode_dataframe_threaded(df_entree.copy(), addr_cols, lat_out_col, lon_out_col, user_agent, log_area_ref, self.update_progress)

            if df_sortie is not None:
                log_message(log_area_ref, f"Sauvegarde du fichier géocodé: {output_file}")
                df_sortie.to_excel(output_file, index=False, engine='openpyxl')
                log_message(log_area_ref, f"Terminé avec succès ! Fichier sauvegardé: {os.path.abspath(output_file)}")
                messagebox.showinfo("Succès", f"Géocodage terminé avec succès !\nFichier sauvegardé ici : {os.path.abspath(output_file)}")
            else:
                log_message(log_area_ref, "Le processus de géocodage a échoué dans le thread.")
                messagebox.showerror("Erreur", "Le processus de géocodage a rencontré une erreur. Vérifiez le journal.")

        except Exception as e:
            error_msg = f"ERREUR majeure lors du processus: {e}"
            log_message(log_area_ref, error_msg)
            messagebox.showerror("Erreur Critique", error_msg)
        finally:
            # Réactiver le bouton, que ce soit un succès ou une erreur
            # Doit être fait dans le thread principal si Tkinter est sensible
            self.master.after(0, self.enable_run_button)

    def enable_run_button(self):
        self.run_button.config(state="normal", text="Lancer le Géocodage")

# --- Lancement de l'application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = GeocoderApp(root)
    root.mainloop()