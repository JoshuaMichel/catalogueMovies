import os
import cv2
import argparse
import pyzbar.pyzbar as pyzbar
import requests
import csv

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

def lookup_movie_name(serial_number):
    # Example of an online barcode lookup service URL
    url = f"https://example.com/barcode/{serial_number}"
    
    # Send GET request to the URL
    response = requests.get(url)
    
    # Extract movie name from the response
    # (Replace this logic with the actual implementation for the chosen barcode lookup service)
    movie_name = "Movie Name Placeholder"
    
    return movie_name

def detect_and_draw_barcode(input_folder, output_folder):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Initialize a set to store unique serial numbers and their corresponding image files
    unique_barcodes = set()

    # Get list of image files in the input folder
    image_files = [f for f in os.listdir(input_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    # Open CSV file to write barcode information
    output_csv_path = os.path.join(output_folder, "detected_barcodes.csv")
    with open(output_csv_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Serial Code', 'Movie Name'])  # Write header row
        for image_file in image_files:
            # Read the image
            image_path = os.path.join(input_folder, image_file)
            image = cv2.imread(image_path)
            if image is None:
                print(f"Unable to read image: {image_file}")
                continue

            # Detect barcodes in the image
            bounding_boxes, serial_numbers = detect_barcodes(image)

            # Write detected serial numbers and corresponding movie names to CSV
            for serial_number in serial_numbers:
                movie_name = lookup_movie_name(serial_number)
                unique_barcodes.add((serial_number, image_file, movie_name))
                csv_writer.writerow([serial_number, movie_name])

            # Draw bounding boxes around detected barcodes
            image_with_boxes = draw_bounding_boxes(image.copy(), bounding_boxes)

            # Write the image with bounding boxes to the output folder
            output_image_path = os.path.join(output_folder, image_file)
            cv2.imwrite(output_image_path, image_with_boxes)
            print(f"Processed image: {image_file} -> {output_image_path}")

    # Write unique barcode information to CSV
    with open(output_csv_path, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Unique Detected Barcodes', 'Image'])
        for barcode_info in unique_barcodes:
            csv_writer.writerow([barcode_info[0], barcode_info[2]])

    print(f"Barcode information saved to: {output_csv_path}")

if __name__ == "__main__":
    # Create ArgumentParser object
    parser = argparse.ArgumentParser(description="Object detect barcodes in images and draw bounding boxes")

    # Add arguments
    parser.add_argument("input_folder", help="Path to the input folder containing images with barcodes")
    parser.add_argument("output_folder", help="Path to the output folder to save images with bounding boxes and detected barcode information")

    # Parse arguments
    args = parser.parse_args()

    # Call the function to detect and draw barcodes
    detect_and_draw_barcode(args.input_folder, args.output_folder)
