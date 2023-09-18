import tkinter as tk
import requests
from bs4 import BeautifulSoup
import pandas as pd


def generate_starting_list():
    # Get the input values from the GUI
    url = url_entry.get()
    cup = cup_var.get()
    desired_event = event_entry.get()

    # Send a GET request to the target page
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table element by its ID or class
    table = soup.find('table', id='ft')  # Replace with the appropriate ID or None to ignore

    # Check if the table exists
    if table is not None:
        # Extract the table data into a pandas DataFrame
        headers = []
        data = []

        # Extract the table headers
        for th in table.find_all('th'):
            headers.append(th.text.strip())

        # Extract the table rows
        for row in table.find_all('tr'):
            row_data = []
            for cell in row.find_all('td'):
                row_data.append(cell.text.strip())
            if len(row_data) == len(headers):
                data.append(row_data)

        # Filter the data based on the desired event
        # Desired event = 'xxxm XX Cat A Women/Men', relays = '4xXXm XX (Mixed) Cat A (Women/Men)'
        # desired_event = '400m SF Cat A Women'  # Replace with the desired event name
        filtered_data = [row for row in data if row[7] == desired_event]  # Assuming the event column is at index 3

        df = pd.DataFrame(filtered_data)

        # Format the time column
        time_column_index = 3  # Index of the time column
        time_column = df.iloc[:, time_column_index]

        formatted_times = []
        for time_value in time_column:
            parts = time_value.split('/')
            time_parts = [part.strip().split(':') for part in parts]
            formatted_time_parts = []
            for time_part in time_parts:
                if len(time_part) == 2:
                    if time_part[0].upper() == 'MIN':
                        minutes = time_part[1]
                        if len(minutes) == 1:
                            minutes = '0' + minutes
                        formatted_time_parts.append(minutes)
                        formatted_time_parts.append(':')
                    if time_part[0].upper() == 'SEC':
                        seconds = time_part[1]
                        if len(seconds) == 1:
                            seconds = '0' + seconds
                        formatted_time_parts.append(seconds)
                        formatted_time_parts.append(',')
                    elif time_part[0].upper() == 'HUN':
                        hundreds = time_part[1]
                        if len(hundreds) == 1:
                            hundreds = '0' + hundreds
                        formatted_time_parts.append(hundreds)
            formatted_time = ''.join(formatted_time_parts)
            formatted_times.append(formatted_time)

        # Update the time column in the DataFrame
        df.iloc[:, time_column_index] = formatted_times

        # Keep only columns 2 and 3, and rearrange them to columns 0 and 1
        df = df.iloc[:, [2, 3]]

        # Sort entries by time in ascending order
        df_sorted = df.sort_values(by=df.columns[1], ascending=True).reset_index(drop=True)

        # Determine the number of entries and heats
        num_entries = len(df_sorted)
        num_heats = num_entries // 8 + 1

        if num_heats == 0:
            print("Insufficient entries to form heats.")
            exit()

        print("Number of heats:", num_heats)

        # Assign heats and lanes to entries
        lanes_order = [4, 5, 3, 6, 2, 7, 1, 8]  # Standard alley (outside-in)

        heats = []

        if not cup:
            if desired_event != '400m IM Cat A Women' and desired_event != '400m IM Cat A Men' and desired_event != \
                    '800m SF Cat A Women' and desired_event != '800m SF Cat A Men' and desired_event != '1500m SF Cat A Men' \
                    and desired_event != '1500m SF Cat A Women':
                seeding_order = [4, 5, 3, 6, 2, 7, 1, 8]  # Circle seeding
                for heat_num in range(num_heats):
                    heat_entries = []
                    start_entry = heat_num
                    entry_index = start_entry

                    while entry_index < num_entries:
                        heat_entries.append(df_sorted.iloc[entry_index].values)
                        entry_index += num_heats

                    heats.append({'heat': heat_num + 1, 'entries': heat_entries})

                # Rearrange entries based on seeding order (Circle seeding)
                for heat in heats:
                    heat_entries = []
                    for i, entry in enumerate(heat['entries']):
                        entry_index = i % len(seeding_order)
                        heat_entries.append(heat['entries'][entry_index])
                    heat['entries'] = heat_entries

                # Truncate extra entries in the last heat if necessary
                if num_heats > 1:
                    num_entries_per_heat = num_entries // num_heats
                    num_extra_entries = num_entries % num_heats
                    if num_extra_entries > 0:
                        heats[-1]['entries'] = heats[-1]['entries'][:num_entries_per_heat]

            else:
                for heat_num in range(num_heats):
                    start_entry = heat_num * len(lanes_order)
                    heat_entries = df_sorted.iloc[start_entry: start_entry + len(lanes_order)].values.tolist()
                    heats.append({'heat': heat_num + 1, 'entries': heat_entries})
        else:
            for heat_num in range(num_heats):
                start_entry = heat_num * len(lanes_order)
                heat_entries = df_sorted.iloc[start_entry: start_entry + len(lanes_order)].values.tolist()
                heats.append({'heat': heat_num + 1, 'entries': heat_entries})

        # Reverse the order of heats
        heats.reverse()

        # Save the heats and lanes information to a new Excel file
        heats_data = []
        for heat in heats:
            for i, entry in enumerate(heat['entries']):
                heats_data.append([lanes_order[i], entry[0], entry[1], num_heats - heat['heat'] + 1])  # Replace 1 and 0
                # with the correct column indexes of the 'time' and 'name' columns

        # Create a DataFrame for the heats data
        heats_df = pd.DataFrame(heats_data, columns=['Lane', 'Name', 'Time', 'Heat'])

        # Sort the heats DataFrame by lane number and heat number
        heats_df_sorted = heats_df.sort_values(by=['Lane', 'Heat'], ascending=[True, True])

        # Create a blank row between heats
        heats_df_with_blank_rows = heats_df_sorted.groupby('Heat', as_index=False).apply(
            lambda x: pd.concat([x, pd.DataFrame('', index=[0], columns=x.columns)]))

        # Reset the index of the DataFrame
        heats_df_with_blank_rows = heats_df_with_blank_rows.reset_index(drop=True)

        # Save the sorted heats DataFrame with blank rows to a new Excel file
        heats_df_with_blank_rows.to_excel('vahetused.xlsx', index=False)
        print('Excel file with sorted heats generated successfully!')
    else:
        print('Table element not found on the page.')


# Create the main window
window = tk.Tk()
window.title("Starting List Generator")
window.geometry('620x300')

# Create the URL label and entry
url_label = tk.Label(window, text="89 lingi lõpus on EM\nURL:")
url_label.pack()
default_url = "https://www.sportdata.org/cmas/set-online/popup_nennungen_main.php?popup_action=nennungenall&verid=89"
url_entry = tk.Entry(window, width=200)
url_entry.insert(tk.END, default_url)  # Set default URL
url_entry.pack()

# Create the cup checkbox
cup_var = tk.BooleanVar()
cup_checkbox = tk.Checkbutton(window, text="Maailma Karikas", variable=cup_var)
cup_checkbox.pack()

# Create the event label and entry
event_label = tk.Label(window, text="Individuaalsed alad nt: 50m SF Cat A Men\nTeated nt: 4x50m SF Mixed Cat A või "
                                    "4x100m SF Cat A Women\nAla:")
event_label.pack()
event_entry = tk.Entry(window, width=50)
event_entry.pack()

location_label = tk.Label(window, text="Windows arvutites excel tabel ilmub samas kaustas, kus see fail on.\nMacOS arvutites excel tabel ilmub teie Home kaustas"
                                       "(selle kausta nimi on teie kasutajanimi).")
location_label.pack()
# Create the generate button
generate_button = tk.Button(window, text="Generate Starting List", command=generate_starting_list)
generate_button.pack()

# Run the GUI main loop
window.mainloop()
