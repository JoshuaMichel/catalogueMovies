import os
import cv2
import argparse
import pyzbar.pyzbar as pyzbar
import requests
import csv
import sqlite3
from datetime import datetime

def detect_barcodes(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect barcodes in the grayscale image
    barcodes = pyzbar.decode(gray)

    # Convert the list of barcodes to a list of bounding box coordinates
    bounding_boxes = []
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        bounding_boxes.append((x, y, w, h))

    # Extract and return serial numbers of detected barcodes
    serial_numbers = [barcode.data.decode('utf-8') for barcode in barcodes]
    return bounding_boxes, serial_numbers

def draw_bounding_boxes(image, bounding_boxes):
    # Loop through detected barcodes and draw bounding boxes
    for bbox in bounding_boxes:
        x, y, w, h = bbox
        cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)

    return image

def lookup_movie_info(serial_number):
    # Send GET request to UPC Item Database API
    url = "https://api.upcitemdb.com/prod/trial/lookup"
    params = {
        'upc': serial_number
    }
    response = requests.get(url, params=params)
    print("Response: ", response)  # Keep this for debugging purposes
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.json().get('message', 'Unknown error')}")
        return None

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS barcodes (
        id INTEGER PRIMARY KEY,
        serial_code TEXT,
        ean TEXT,
        title TEXT,
        upc TEXT,
        gtin TEXT,
        asin TEXT,
        description TEXT,
        brand TEXT,
        model TEXT,
        dimension TEXT,
        weight TEXT,
        category TEXT,
        currency TEXT,
        lowest_recorded_price REAL,
        highest_recorded_price REAL,
        images TEXT,
        offers TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_duplicate TEXT
    )
    ''')
    conn.commit()
    conn.close()

def insert_into_database(db_path, serial_code, data):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM barcodes WHERE serial_code = ?', (serial_code,))
    exists = cursor.fetchone()

    if exists:
        is_duplicate = 'Yes'
    else:
        is_duplicate = 'No'

    cursor.execute('''
    INSERT INTO barcodes (
        serial_code, ean, title, upc, gtin, asin, description, brand, model,
        dimension, weight, category, currency, lowest_recorded_price, 
        highest_recorded_price, images, offers, is_duplicate
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        serial_code,
        data.get('ean', ''),
        data.get('title', ''),
        data.get('upc', ''),
        data.get('gtin', ''),
        data.get('asin', ''),
        data.get('description', ''),
        data.get('brand', ''),
        data.get('model', ''),
        data.get('dimension', ''),
        data.get('weight', ''),
        data.get('category', ''),
        data.get('currency', ''),
        data.get('lowest_recorded_price', 0.0),
        data.get('highest_recorded_price', 0.0),
        ', '.join(data.get('images', [])),
        ', '.join([
            f"{offer.get('merchant', '')} - {offer.get('price', '')}" 
            for offer in data.get('offers', [])
        ]),
        is_duplicate
    ))
    conn.commit()
    conn.close()

def detect_and_draw_barcode(input_folder, output_folder, db_path):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Initialize a dictionary to store unique serial numbers and their corresponding movie names
    unique_barcodes = {}

    # Get list of image files in the input folder
    image_files = [f for f in os.listdir(input_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    # Open CSV file to write barcode information
    output_csv_path = os.path.join(output_folder, "detected_barcodes.csv")
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=[
            'Serial Code', 'EAN', 'Title', 'UPC', 'GTIN', 'ASIN', 'Description', 'Brand',
            'Model', 'Dimension', 'Weight', 'Category', 'Currency', 'Lowest Recorded Price',
            'Highest Recorded Price', 'Images', 'Offers', 'Timestamp', 'Is Duplicate'
        ])
        csv_writer.writeheader()
        for image_file in image_files:
            # Read the image
            image_path = os.path.join(input_folder, image_file)
            image = cv2.imread(image_path)
            if image is None:
                print(f"Unable to read image: {image_file}")
                continue

            # Detect barcodes in the image
            _, serial_numbers = detect_barcodes(image)

            # Write detected serial numbers and corresponding movie information to CSV and database
            for serial_number in serial_numbers:
                if serial_number not in unique_barcodes:
                    barcode_info = lookup_movie_info(serial_number)
                    if barcode_info:
                        items = barcode_info.get('items', [])
                        for item in items:
                            # Prepare the row for CSV
                            row = {
                                'Serial Code': serial_number,
                                'EAN': item.get('ean', ''),
                                'Title': item.get('title', ''),
                                'UPC': item.get('upc', ''),
                                'GTIN': item.get('gtin', ''),
                                'ASIN': item.get('asin', ''),
                                'Description': item.get('description', ''),
                                'Brand': item.get('brand', ''),
                                'Model': item.get('model', ''),
                                'Dimension': item.get('dimension', ''),
                                'Weight': item.get('weight', ''),
                                'Category': item.get('category', ''),
                                'Currency': item.get('currency', ''),
                                'Lowest Recorded Price': item.get('lowest_recorded_price', 0.0),
                                'Highest Recorded Price': item.get('highest_recorded_price', 0.0),
                                'Images': ', '.join(item.get('images', [])),
                                'Offers': ', '.join([
                                    f"{offer.get('merchant', '')} - {offer.get('price', '')}" 
                                    for offer in item.get('offers', [])
                                ]),
                                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'Is Duplicate': 'No' if serial_number not in unique_barcodes else 'Yes'
                            }

                            # Write to CSV
                            csv_writer.writerow(row)

                            # Insert into database
                            insert_into_database(db_path, serial_number, item)

                        unique_barcodes[serial_number] = True

            # Draw bounding boxes around detected barcodes
            image_with_boxes = draw_bounding_boxes(image.copy(), [])

            # Write the image with bounding boxes to the output folder
            output_image_path = os.path.join(output_folder, image_file)
            cv2.imwrite(output_image_path, image_with_boxes)
            print(f"Processed image: {image_file} -> {output_image_path}")

    print(f"Barcode information saved to: {output_csv_path}")

if __name__ == "__main__":
    # Create ArgumentParser object
    parser = argparse.ArgumentParser(description="Object detect barcodes in images and draw bounding boxes")

    # Add arguments
    parser.add_argument("input_folder", help="Path to the input folder containing images with barcodes")
    parser.add_argument("output_folder", help="Path to the output folder to save images with bounding boxes and detected barcode information")
    parser.add_argument("db_path", help="Path to the SQLite database file")

    # Parse arguments
    args = parser.parse_args()

    # Create database and table if it doesn't exist
    create_database(args.db_path)

    # Call the function to detect and draw barcodes
    detect_and_draw_barcode(args.input_folder, args.output_folder, args.db_path)
