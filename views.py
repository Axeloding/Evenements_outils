# events/views.py

import pandas as pd
import folium
from folium.plugins import MarkerCluster
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .models import Event, UploadedFile 
from .forms import ExcelUploadForm 
import traceback
from django.core.cache import cache
from django.utils.html import escape
from django.conf import settings 
import os
from django.http import FileResponse

# --- CONSTANTES DE COLONNES ---
EVENT_NAME_COL = "Nom Lieu / Promoter"
CITY_COL = "Ville"
COUNTRY_COL = "Pays"
LATITUDE_COL = "Latitude_Geocodee"
LONGITUDE_COL = "Longitude_Geocodee"
DESCRIPTION_COL = "Comments"
EVENT_DATE_COL = "Event dates"
MAIL_COL = "Mail"
BOOKER_NAME_COL = "Booker name"
PROMOTER_TYPE_COL = "Promoter Type"
STYLE_COL = "Style"

# --- home_view (Avec MarkerCluster, filtres, popups détaillés, cache) ---
@login_required
def home_view(request):
    selected_promoter_type = request.GET.get('promoter_type_filter', None)
    search_query_city = request.GET.get('search_city', "").strip()
    search_query_country = request.GET.get('search_country', "").strip()

    events_base_query = Event.objects.select_related('added_by').all()

    if selected_promoter_type and selected_promoter_type != "":
        events_base_query = events_base_query.filter(promoter_type=selected_promoter_type)
    if search_query_city:
        events_base_query = events_base_query.filter(city__icontains=search_query_city)
    if search_query_country:
        events_base_query = events_base_query.filter(country__icontains=search_query_country) 
    
    events_for_table_list = list(events_base_query.order_by('-created_at'))
    events_with_coords_list = [
        event for event in events_for_table_list 
        if event.latitude is not None and event.longitude is not None and \
           isinstance(event.latitude, float) and isinstance(event.longitude, float)
    ]
    
    all_events_count_total_in_db = Event.objects.count()
    map_html = None
    
    cache_key_promoter_types = 'all_event_promoter_types_v2.4' 
    all_promoter_types_for_filter = cache.get(cache_key_promoter_types)
    if all_promoter_types_for_filter is None:
        all_promoter_types_for_filter_qs = Event.objects.filter(
            promoter_type__isnull=False, promoter_type__gt=''
        ).values_list('promoter_type', flat=True).distinct().order_by('promoter_type')
        all_promoter_types_for_filter = list(all_promoter_types_for_filter_qs)
        cache.set(cache_key_promoter_types, all_promoter_types_for_filter, timeout=3600)

    if events_with_coords_list:
        valid_lats_map = [e.latitude for e in events_with_coords_list]
        valid_lons_map = [e.longitude for e in events_with_coords_list]
        map_center_location = [46.2276, 2.2137]; current_zoom = 2
        if valid_lats_map and valid_lons_map:
            avg_lat = sum(valid_lats_map) / len(valid_lats_map)
            avg_lon = sum(valid_lons_map) / len(valid_lons_map)
            map_center_location = [avg_lat, avg_lon]
            if search_query_city and len(events_with_coords_list) > 0: current_zoom = 10
            elif (search_query_country or selected_promoter_type) and len(events_with_coords_list) > 0 :
                if len(events_with_coords_list) == 1: current_zoom = 13
                elif len(events_with_coords_list) < 10: current_zoom = 9
                elif len(events_with_coords_list) < 50: current_zoom = 7
                else: current_zoom = 6
            elif len(events_with_coords_list) > 0 : current_zoom = 4
        
        m = folium.Map(location=map_center_location, zoom_start=current_zoom, tiles="CartoDB positron", control_scale=True)
        marker_cluster = MarkerCluster(name="Événements", options={'maxClusterRadius': 40, 'spiderfyOnMaxZoom': True, 'showCoverageOnHover': False}).add_to(m)

        for event in events_with_coords_list:
            event_name_safe = escape(event.name or 'N/A'); promoter_type_safe = escape(event.promoter_type or '')
            style_safe = escape(event.style or ''); city_safe = escape(event.city or ''); country_safe = escape(event.country or '')
            added_by_user = escape(event.added_by.username) if event.added_by else "Système"; booker_name_safe = escape(event.booker_name or '')
            description_safe = escape(event.description or '')
            popup_lines = []
            popup_lines.append(f"""<h5 style="margin:0 0 10px 0;padding-bottom:7px;border-bottom:2px solid #00aeff;color:#007bff;font-size:16px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{event_name_safe}"><i class="bi bi-pin-map-fill" style="color:#00aeff;font-size:1em;vertical-align:-0.1em;"></i> {event_name_safe}</h5>""")
            if city_safe or country_safe: loc_parts = [p for p in [city_safe,country_safe] if p]; popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-geo-alt-fill" style="color:#0d6efd;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Lieu:</strong> {', '.join(loc_parts)}</div></li>""")
            if event.event_date: popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-calendar3-event-fill" style="color:#198754;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Date:</strong> {event.event_date.strftime('%d %b %Y, %H:%M') if event.event_date else 'N/A'}</div></li>""")
            if promoter_type_safe: popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-building" style="color:#6f42c1;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Type Promoteur:</strong> {promoter_type_safe}</div></li>""")
            if style_safe: popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-music-note-list" style="color:#fd7e14;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Style:</strong> {style_safe}</div></li>""")
            if event.contact_email:
                emails=[e.strip() for e in event.contact_email.replace(';',',').split(',') if e.strip()];first_email=emails[0] if emails else "";display_emails=escape(", ".join(emails)) if emails else "N/F"
                email_html=display_emails;popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-envelope-at" style="color:#dc3545;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Email:</strong> <a href="mailto:{escape(first_email)}" style="color:#0056b3;">{email_html}</a></div></li>""" if first_email else f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-envelope-at" style="color:#dc3545;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Email:</strong> {email_html}</div></li>""")
            if booker_name_safe: popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;"><i class="bi bi-person-lines-fill" style="color:#0dcaf0;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><strong>Booker:</strong> {booker_name_safe}</div></li>""")
            popup_lines.append(f"""<li style="margin-bottom:6px;display:flex;align-items:flex-start;font-size:0.9em;color:#6c757d;"><i class="bi bi-person-fill-add" style="color:#6c757d;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div><i>Ajouté par: {added_by_user}</i></div></li>""")
            if description_safe: desc_s=description_safe[:80]+"..." if len(description_safe)>80 else description_safe;popup_lines.append(f"""<li style="margin-top:8px;padding-top:8px;border-top:1px dashed #ced4da;display:flex;align-items:flex-start;"><i class="bi bi-card-text" style="color:#6c757d;margin-right:8px;font-size:1.1em;margin-top:2px;"></i><div style="font-style:italic;color:#495057;">{desc_s}</div></li>""")
            popup_ul = "<ul style=\"list-style-type:none;padding:0;margin:0;\">" + "".join(popup_lines) + "</ul>"
            popup_html_f = f"""<div style="font-family:'Arial',sans-serif;font-size:12px;color:#333;width:300px;line-height:1.5;">{popup_ul}<div style="font-size:0.8em;color:#6c757d;margin-top:8px;text-align:right;border-top:1px solid #e9ecef;padding-top:5px;">ID:{event.pk} | <i class="bi bi-geo"></i> {event.latitude:.4f},{event.longitude:.4f}</div></div>"""
            html_iframe = f"""<html><head><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"><style>body{{margin:0;padding:12px;background-color:#fff;overflow-y:auto;}}ul{{list-style-type:none;padding:0;margin:0 !important;}}a{{color:#0056b3;text-decoration:none;}}a:hover{{text-decoration:underline!important;}}</style></head><body>{popup_html_f}</body></html>"""
            iframe = folium.IFrame(html_iframe, width=340, height=310);popup=folium.Popup(iframe,max_width=350)
            icon_marker = folium.Icon(color='darkblue',icon_color='white',icon='fa-map-marker-alt',prefix='fa')
            if event.promoter_type: pt_s=event.promoter_type.lower(); # Correction: indentation de cette ligne
            if event.promoter_type and "festival" in pt_s: icon_marker=folium.Icon(color='red',icon='fa-flag',prefix='fa')
            elif event.promoter_type and "club" in pt_s: icon_marker=folium.Icon(color='blue',icon='fa-music',prefix='fa')
            elif event.promoter_type and ("concert" in pt_s or "hall" in pt_s): icon_marker=folium.Icon(color='green',icon='fa-industry',prefix='fa')
            folium.Marker(location=[event.latitude,event.longitude],popup=popup,tooltip=f"{escape(event.name or '')} ({escape(event.promoter_type or 'N/D')})",icon=icon_marker).add_to(marker_cluster)
        map_html = m._repr_html_()
    
    context = {'map_html':map_html,'event_count_total_db':all_events_count_total_in_db,'events_on_map_count':len(events_with_coords_list),'events_for_table':events_for_table_list,'events_in_table_count':len(events_for_table_list),'all_promoter_types':all_promoter_types_for_filter,'selected_promoter_type_filter':selected_promoter_type,'current_search_city':search_query_city,'current_search_country':search_query_country}
    return render(request, 'events/home.html', context)

# --- VUE POUR L'UPLOAD DE FICHIER EXCEL (AVEC MESSAGES RÉCAPITULATIFS CORRIGÉS) ---
@login_required
def upload_excel_view(request):
    current_form = ExcelUploadForm() 
    if request.method == 'POST':
        posted_form = ExcelUploadForm(request.POST, request.FILES)
        if posted_form.is_valid():
            excel_file = request.FILES['excel_file']
            uploaded_file_instance = UploadedFile(file=excel_file, uploaded_by=request.user); uploaded_file_instance.save()
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                if EVENT_NAME_COL not in df.columns: 
                    messages.error(request, f"La colonne obligatoire '{EVENT_NAME_COL}' est manquante.")
                    # Pas de redirect ici, le render final affichera l'erreur avec current_form (vide).
                else:
                    imported_count=0; skipped_count=0; imported_without_coords_count=0 
                    date_format_warnings_count=0; coord_format_warnings_count=0
                    
                    for index, row in df.iterrows():
                        try:
                            name_val = row.get(EVENT_NAME_COL)
                            name = str(name_val).strip() if pd.notna(name_val) and str(name_val).strip() else None
                            if not name: 
                                messages.warning(request, f"Ligne {index+2}: Nom ('{EVENT_NAME_COL}') manquant. Ignorée.")
                                skipped_count += 1; continue
                            
                            lat, lon = None, None
                            lat_excel_val = row.get(LATITUDE_COL)
                            if pd.notna(lat_excel_val):
                                lat_str_val = str(lat_excel_val).strip().lower() # Correction: utiliser lat_str_val ici
                                if lat_str_val not in ["", "non trouvé", "not found"]:
                                    try: lat = float(str(lat_excel_val).replace(',', '.')) # Revenir à lat_excel_val pour la conversion
                                    except ValueError: coord_format_warnings_count +=1
                            
                            lon_excel_val = row.get(LONGITUDE_COL)
                            if pd.notna(lon_excel_val):
                                lon_str_val = str(lon_excel_val).strip().lower() # Correction: utiliser lon_str_val ici
                                if lon_str_val not in ["", "non trouvé", "not found"]:
                                    try: lon = float(str(lon_excel_val).replace(',', '.')) # Revenir à lon_excel_val pour la conversion
                                    except ValueError: coord_format_warnings_count +=1
                            
                            if lat is None or lon is None: imported_without_coords_count += 1
                            
                            city = None; country = None; description = None; contact_email = None
                            booker_name_val = None; promoter_type_val = None; style_val = None; event_date_obj = None

                            if CITY_COL in df.columns and pd.notna(row.get(CITY_COL)): city = str(row.get(CITY_COL, '')).strip()
                            if COUNTRY_COL in df.columns and pd.notna(row.get(COUNTRY_COL)): country = str(row.get(COUNTRY_COL, '')).strip()
                            if DESCRIPTION_COL in df.columns and pd.notna(row.get(DESCRIPTION_COL)): description = str(row.get(DESCRIPTION_COL, '')).strip()
                            if MAIL_COL in df.columns and pd.notna(row.get(MAIL_COL)): contact_email = str(row.get(MAIL_COL, '')).strip()
                            if BOOKER_NAME_COL in df.columns and pd.notna(row.get(BOOKER_NAME_COL)): booker_name_val = str(row.get(BOOKER_NAME_COL, '')).strip()
                            if PROMOTER_TYPE_COL in df.columns and pd.notna(row.get(PROMOTER_TYPE_COL)): promoter_type_val = str(row.get(PROMOTER_TYPE_COL, '')).strip()
                            if STYLE_COL in df.columns and pd.notna(row.get(STYLE_COL)): style_val = str(row.get(STYLE_COL, '')).strip()
                            
                            if EVENT_DATE_COL in df.columns and pd.notna(row.get(EVENT_DATE_COL)):
                                event_date_str = str(row.get(EVENT_DATE_COL, '')).strip()
                                if event_date_str:
                                    try: event_date_obj = pd.to_datetime(event_date_str, errors='raise').to_pydatetime()
                                    except (ValueError, TypeError): date_format_warnings_count += 1
                            
                            event_data = {'name':name,'city':city,'country':country,'latitude':lat,'longitude':lon,'description':description,'event_date':event_date_obj,'contact_email':contact_email,'booker_name':booker_name_val,'promoter_type':promoter_type_val,'style':style_val,'added_by':request.user}
                            Event.objects.create(**event_data)
                            imported_count += 1
                        except Exception as e_row: 
                            messages.error(request, f"Erreur critique lors du traitement de la ligne {index+2} ('{row.get(EVENT_NAME_COL, 'Nom inconnu')}') : {type(e_row).__name__} - {e_row}. Ligne ignorée.")
                            skipped_count += 1
                    
                    if imported_count > 0: messages.success(request, f"{imported_count} événements traités et enregistrés.")
                    if imported_without_coords_count > 0: messages.info(request, f"{imported_without_coords_count} événements ont été enregistrés sans coordonnées GPS valides (n'apparaîtront pas sur la carte).")
                    if coord_format_warnings_count > 0: messages.warning(request, f"Pour {coord_format_warnings_count} événements, les valeurs de latitude/longitude fournies n'étaient pas des nombres valides (hors 'Non trouvé') et leurs coordonnées ont été ignorées.")
                    if date_format_warnings_count > 0: messages.warning(request, f"{date_format_warnings_count} dates d'événements n'ont pas pu être reconnues et ont été ignorées.")
                    if skipped_count > 0: messages.warning(request, f"{skipped_count} lignes du fichier Excel ont été complètement ignorées.")
                    if imported_count==0 and skipped_count==0 and not df.empty: messages.info(request, "Fichier traité, mais aucune donnée d'événement valide n'a été extraite ou toutes les lignes ont été filtrées/ignorées.")
                    elif df.empty: messages.info(request, "Le fichier Excel était vide.")
                    
                    cache.delete(cache_key_promoter_types)
                    # print(f"DEBUG: Cache {cache_key_promoter_types} vidé après import.")
                    return redirect('events:home')

            except pd.errors.EmptyDataError: messages.error(request, "Le fichier Excel semble vide ou n'a pas pu être lu.")
            except Exception as e: 
                messages.error(request, f"Erreur générale lors du traitement du fichier Excel : {e}")
                print(f"Erreur Upload Excel: {type(e).__name__} - {e}"); traceback.print_exc()
        else: 
            current_form = posted_form
            error_list_display = [];
            for field_name, error_list_for_field in posted_form.errors.items(): 
                label=posted_form.fields[field_name].label if field_name!='__all__' and field_name in posted_form.fields else 'Formulaire'
                for error_msg in error_list_for_field: error_list_display.append(f"{label}: {error_msg}")
            messages.error(request, f"Veuillez corriger les erreurs dans le formulaire d'upload : {' | '.join(error_list_display)}")
    
    context = {'form': current_form, 'EVENT_NAME_COL':EVENT_NAME_COL, 'CITY_COL':CITY_COL, 'COUNTRY_COL':COUNTRY_COL, 'LATITUDE_COL':LATITUDE_COL, 'LONGITUDE_COL':LONGITUDE_COL, 'DESCRIPTION_COL':DESCRIPTION_COL, 'EVENT_DATE_COL':EVENT_DATE_COL, 'MAIL_COL':MAIL_COL, 'BOOKER_NAME_COL':BOOKER_NAME_COL, 'PROMOTER_TYPE_COL':PROMOTER_TYPE_COL, 'STYLE_COL':STYLE_COL}
    return render(request, 'events/upload_excel.html', context)

# --- VUES D'AUTHENTIFICATION ---
def login_view(request):
    if request.user.is_authenticated: messages.info(request, "Vous êtes déjà connecté."); return redirect('events:home') 
    form_to_render_login = AuthenticationForm()
    if request.method == 'POST':
        form_from_post_login = AuthenticationForm(request, data=request.POST)
        if form_from_post_login.is_valid():
            username = form_from_post_login.cleaned_data.get('username'); password = form_from_post_login.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user); messages.success(request, f"Bienvenue {username}! Vous êtes maintenant connecté."); next_page = request.GET.get('next') 
                return redirect(next_page) if next_page else redirect('events:home')
            else: messages.error(request, "Nom d'utilisateur ou mot de passe incorrect."); form_to_render_login = form_from_post_login
        else:
            error_list = [];
            for field, errors_list_for_field in form_from_post_login.errors.items():
                label=form_from_post_login.fields[field].label if field!='__all__' and field in form_from_post_login.fields else ''; [error_list.append(f"{label}: {err}".strip(': ')) for err in errors_list_for_field]
            messages.error(request, f"Erreurs dans le formulaire de connexion : {' | '.join(error_list) if error_list else 'Veuillez corriger les erreurs.'}"); form_to_render_login = form_from_post_login
    return render(request, 'events/login.html', {'login_form': form_to_render_login})

@login_required
def logout_view(request):
    logout(request); messages.info(request, "Vous avez été déconnecté avec succès."); return redirect('events:home')

# --- VUE POUR TÉLÉCHARGER LE TEMPLATE EXCEL ---
@login_required 
def download_template_view(request):
    file_path = os.path.join(settings.BASE_DIR, 'events', 'static', 'events', 'files', 'template_evenements.xlsx')
    if os.path.exists(file_path):
        try: 
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='template_evenements.xlsx')
        except Exception as e: 
            messages.error(request, f"Impossible de télécharger le fichier template : {e}")
    else: 
        messages.error(request, "Fichier template non trouvé sur le serveur. Veuillez contacter l'administrateur.")
    return redirect('events:upload_excel')