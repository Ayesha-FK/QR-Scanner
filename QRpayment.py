import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import re
import json
import time
import qrcode
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av

# Set page configuration
st.set_page_config(
    page_title="QR Payment System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #3F51B5;
    text-align: center;
    margin-bottom: 1rem;
    font-weight: bold;
}
.sub-header {
    font-size: 1.5rem;
    color: #303F9F;
    margin-bottom: 1rem;
}
.info-box {
    background-color: #E8EAF6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #3F51B5;
    color: #000000;
}
.success-box {
    background-color: #E8F5E9;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #4CAF50;
    color: #000000;
}
.error-box {
    background-color: #FFEBEE;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #F44336;
    color: #000000;
}
.warning-box {
    background-color: #FFF8E1;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #FFC107;
    color: #000000;
}
.qr-container {
    display: flex;
    justify-content: center;
    margin: 2rem 0;
}
.result-text {
    font-size: 1.2rem;
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #4CAF50;
    color: #000000;
}
.status-text {
    font-size: 1rem;
    color: #FF5722;
}
.success-text {
    font-size: 1.2rem;
    color: #4CAF50;
    font-weight: bold;
}
.centered-image {
    display: flex;
    justify-content: center;
}
.balance-display {
    font-size: 1.5rem;
    font-weight: bold;
    color: #3F51B5;
    text-align: center;
    padding: 1rem;
    background-color: #E8EAF6;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
.tab-content {
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    margin-top: 1rem;
}
.transaction-details {
    background-color: #E3F2FD;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #2196F3;
    color: #000000;
}
</style>
""", unsafe_allow_html=True)

# App title and description
st.markdown('<p class="main-header">QR Payment System</p>', unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_cnic' not in st.session_state:
    st.session_state.user_cnic = ""
if 'balance' not in st.session_state:
    st.session_state.balance = 0.0
if 'qr_result' not in st.session_state:
    st.session_state.qr_result = None
if 'scanning' not in st.session_state:
    st.session_state.scanning = False
if 'payment_confirmed' not in st.session_state:
    st.session_state.payment_confirmed = False
if 'payment_amount' not in st.session_state:
    st.session_state.payment_amount = 0.0
if 'payment_recipient' not in st.session_state:
    st.session_state.payment_recipient = ""
if 'payment_cnic' not in st.session_state:
    st.session_state.payment_cnic = ""
if 'transaction_history' not in st.session_state:
    st.session_state.transaction_history = []
if 'show_my_qr' not in st.session_state:
    st.session_state.show_my_qr = False
if 'scan_state' not in st.session_state:
    st.session_state.scan_state = "idle"  # idle, scanning, detected, confirmed
if 'parsed_payment_data' not in st.session_state:
    st.session_state.parsed_payment_data = None
if 'live_scanning_active' not in st.session_state:
    st.session_state.live_scanning_active = False
if 'camera_started' not in st.session_state:
    st.session_state.camera_started = False # To manage camera resource

# Function to validate CNIC format
def validate_cnic(cnic):
    # Pattern for CNIC: 00000-0000000-0 (exactly this format)
    pattern = r'^\d{5}-\d{7}-\d{1}$'
    return bool(re.match(pattern, cnic))

# Function to generate QR code
# Function to generate QR code (simplified version)
def generate_qr_code(data, box_size=10):
    # Convert data to JSON string
    json_data = json.dumps(data)
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,  # Adjustable box size parameter
        border=4,
    )
    
    # Add data to QR code
    qr.add_data(json_data)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to RGB if not already
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    return img

# Function to detect QR codes
def detect_qr_code(frame):
    # Initialize the QR code detector
    qr_detector = cv2.QRCodeDetector()
    
    # Create a copy of the frame for display
    display_frame = frame.copy()
    qr_value = None
    
    try:
        # For OpenCV 4.5.4 and above, use detectAndDecodeMulti
        ret_qr, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(frame)
        
        # If QR codes are detected
        if ret_qr:
            for s, p in zip(decoded_info, points):
                # If the QR code contains data
                if s:
                    qr_value = s  # Assign the QR code value to the variable
                    color = (0, 255, 0)  # Green color for successful decode
                    
                    # Draw a polygon around the QR code
                    display_frame = cv2.polylines(display_frame, [p.astype(int)], True, color, 8)
                    
                    # Display the decoded text on the frame
                    display_frame = cv2.putText(display_frame, "QR Code Detected", p[0].astype(int), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    break
    except Exception as e:
        # For older versions of OpenCV, use detectAndDecode
        try:
            data, bbox, _ = qr_detector.detectAndDecode(frame)
            
            # If a QR code is detected and contains data
            if bbox is not None and data:
                qr_value = data  # Assign the QR code value to the variable
                
                # Draw a polygon around the QR code
                bbox = bbox.astype(int)
                display_frame = cv2.polylines(display_frame, [bbox], True, (0, 255, 0), 8)
                
                # Display the decoded text on the frame
                display_frame = cv2.putText(display_frame, "QR Code Detected", (bbox[0][0], bbox[0][1] - 10), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        except Exception as e:
            # Just continue if there's an error
            pass
    
    return display_frame, qr_value

# Function to process payment
def process_payment(amount, recipient, cnic):
    if st.session_state.balance >= amount:
        # Update user balance
        st.session_state.balance -= amount
        
        # Record the transaction
        transaction = {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "payment",
            "amount": amount,
            "recipient": recipient,
            "recipient_cnic": cnic,
            "balance_after": st.session_state.balance
        }
        
        st.session_state.transaction_history.append(transaction)
        
        return True, f"Payment of PKR {amount:.2f} to {recipient} was successful."
    else:
        return False, f"Insufficient funds. Your balance is PKR {st.session_state.balance:.2f}."

# Function to parse QR data
def parse_qr_data(qr_data):
    try:
        payment_data = json.loads(qr_data)
        if 'type' in payment_data and payment_data['type'] == 'payment':
            return payment_data, True, "Valid payment QR code detected."
        else:
            return None, False, "Invalid QR code: Not a payment request."
    except Exception as e:
        return None, False, "Error: Could not parse QR code data."

# Function to detect QR code continuously
def detect_qr_code_continuous():
    # Initialize the QR code detector
    qr_detector = cv2.QRCodeDetector()
    
    # Initialize the camera (0 is usually the default camera)
    camera_id = 0
    cap = cv2.VideoCapture(camera_id)
    
    # Check if the camera opened successfully
    if not cap.isOpened():
        st.error("Error: Could not open camera.")
        return None
    
    st.info("Camera opened successfully. Scanning for QR codes...")
    
    # Create a placeholder for the video feed
    video_placeholder = st.empty()
    
    # Variable to store the QR code value
    qr_value = None
    
    # Create a status placeholder
    status_placeholder = st.empty()
    status_placeholder.info("Scanning for QR codes...")
    
    while True:
        # Read a frame from the camera
        ret, frame = cap.read()
        
        if not ret:
            st.error("Error: Failed to capture frame.")
            break
        
        # Create a copy of the frame for display
        display_frame = frame.copy()
        
        # Try to detect and decode QR codes in the frame
        try:
            # For OpenCV 4.5.4 and above, use detectAndDecodeMulti
            ret_qr, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(frame)
            
            # If QR codes are detected
            if ret_qr:
                for s, p in zip(decoded_info, points):
                    # If the QR code contains data
                    if s:
                        qr_value = s  # Assign the QR code value to the variable
                        color = (0, 255, 0)  # Green color for successful decode
                        
                        # Draw a polygon around the QR code
                        display_frame = cv2.polylines(display_frame, [p.astype(int)], True, color, 8)
                        
                        # Display the decoded text on the frame
                        display_frame = cv2.putText(display_frame, s, p[0].astype(int), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        
                        # Convert BGR to RGB for Streamlit display
                        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        
                        # Show the final frame with the detected QR code
                        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                        status_placeholder.success(f"QR Code detected: {s}")
                        
                        # Break the loop after detecting a QR code
                        break
                
                # If we found a valid QR code, break the main loop
                if qr_value:
                    break
                    
        except Exception as e:
            # For older versions of OpenCV, use detectAndDecode
            try:
                data, bbox, _ = qr_detector.detectAndDecode(frame)
                
                # If a QR code is detected and contains data
                if bbox is not None and data:
                    qr_value = data  # Assign the QR code value to the variable
                    
                    # Draw a polygon around the QR code
                    bbox = bbox.astype(int)
                    display_frame = cv2.polylines(display_frame, [bbox], True, (0, 255, 0), 8)
                    
                    # Display the decoded text on the frame
                    display_frame = cv2.putText(display_frame, data, (bbox[0][0], bbox[0][1] - 10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    # Convert BGR to RGB for Streamlit display
                    rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                    
                    # Show the final frame with the detected QR code
                    video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                    status_placeholder.success(f"QR Code detected: {data}")
                    
                    # Break the loop after detecting a QR code
                    break
            except Exception as e:
                # Just continue if there's an error
                pass
        
        # Add status text to the frame
        status_text = "QR Code Scanner - Scanning..."
        cv2.putText(display_frame, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Convert BGR to RGB for Streamlit display
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        
        # Display the frame in Streamlit
        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
        
        # Add a small delay to reduce CPU usage
        time.sleep(0.03)
    
    # Release the camera
    cap.release()
    
    return qr_value

# Function to handle real-time QR code scanning using the local function
def real_time_qr_scan():
    # This function will use the detect_qr_code_continuous function defined in this file
    qr_data = detect_qr_code_continuous()
    return qr_data

# Sidebar with user information and options
with st.sidebar:
    if not st.session_state.user_logged_in:
        st.markdown('<p class="sub-header">Create Account / Login</p>', unsafe_allow_html=True)
        
        # Account creation form
        with st.form("account_form"):
            username = st.text_input("Your Name")
            user_cnic = st.text_input("Your CNIC", placeholder="00000-0000000-0", help="Format must be exactly: 00000-0000000-0")
            initial_balance = st.number_input("Initial Balance (PKR)", min_value=0.0, value=5000.0, format="%.2f")
            
            submitted = st.form_submit_button("Create Account & Login")
            
            if submitted:
                if not username:
                    st.error("Please enter your name.")
                elif not validate_cnic(user_cnic):
                    st.error("CNIC must be in the exact format: 00000-0000000-0")
                else:
                    st.session_state.user_logged_in = True
                    st.session_state.username = username
                    st.session_state.user_cnic = user_cnic
                    st.session_state.balance = initial_balance
                    st.success(f"Welcome, {username}!")
                    st.rerun()
    else:
        st.markdown('<p class="sub-header">User Information</p>', unsafe_allow_html=True)
        st.markdown(f"**Name:** {st.session_state.username}")
        st.markdown(f"**CNIC:** {st.session_state.user_cnic}")
        st.markdown(f'<div class="balance-display">Balance: PKR {st.session_state.balance:.2f}</div>', unsafe_allow_html=True)
        
        if st.button("Logout"):
            # Reset all session state variables
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This app allows you to:
    - Generate QR codes for payments
    - Scan QR codes to make payments
    - Track your account balance
    - View transaction history
    """)

# Run the continuous QR code detection only when explicitly called, not on app startup
if __name__ == "__main__" and False:  # Disabled automatic execution
    print("Starting continuous QR code detection...")
    result = detect_qr_code_continuous()
    
    if result:
        print(f"\nLast detected QR Code Value: {result}")
    else:
        print("\nNo QR code was detected or the camera was closed before detection.")

# Main content
if not st.session_state.user_logged_in:
    st.markdown('<div class="info-box"><h3>Please create an account to use the app</h3></div>', unsafe_allow_html=True)
else:
    # Create tabs for different functionalities
    tab1, tab2, tab3, tab4 = st.tabs(["My QR Code", "Generate Payment QR", "Scan & Pay", "Transaction History"])
    
    # Tab 1: My QR Code
    with tab1:
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Your Personal QR Code</p>', unsafe_allow_html=True)
        
        # Create user data dictionary
        user_data = {
            "type": "user_info",
            "name": st.session_state.username,
            "cnic": st.session_state.user_cnic,
            "balance": st.session_state.balance
        }
        
        # Button to show QR code
        if st.button("Show My QR Code"):
            st.session_state.show_my_qr = True
        
        # Display QR code if button was clicked
        if st.session_state.show_my_qr:
            # Generate QR code with smaller box size for better display
            qr_img = generate_qr_code(user_data, box_size=6)
            
            # Convert PIL image to bytes for Streamlit
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            # Display QR code with controlled width
            st.markdown('<div class="qr-container"></div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(byte_im, caption=f"QR Code for {st.session_state.username}", width=300)
            
            # Display QR code information
            st.markdown(f'''
            <div class="success-box">
                <h3>Your QR Code Information</h3>
                <ul>
                    <li><strong>Name:</strong> {st.session_state.username}</li>
                    <li><strong>CNIC:</strong> {st.session_state.user_cnic}</li>
                    <li><strong>Balance:</strong> PKR {st.session_state.balance:.2f}</li>
                </ul>
                <p>You can download the QR code by right-clicking on the image and selecting "Save Image As..."</p>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="info-box">
                <h3>Instructions</h3>
                <p>Click the "Show My QR Code" button to generate a QR code containing your account information.</p>
                <p>This QR code can be scanned by others to view your account details.</p>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 2: Generate Payment QR
    with tab2:
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Create Payment QR Code</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Payment information form
            with st.form("payment_info_form"):
                # Automatically use the logged-in user's information
                st.markdown(f"**Sender:** {st.session_state.username} (You)")
                amount = st.number_input("Amount (PKR)", min_value=1.0, format="%.2f")
                
                submitted = st.form_submit_button("Generate Payment QR Code")
        
        with col2:
            st.markdown('<p class="sub-header">Generated QR Code</p>', unsafe_allow_html=True)
            qr_placeholder = st.empty()
        
        # Process form submission
        if submitted:
            # Create data dictionary with the logged-in user's information
            payment_data = {
                "type": "payment",
                "sender": st.session_state.username,
                "sender_cnic": st.session_state.user_cnic,
                "amount": amount
            }
            
            # Generate QR code with smaller box size
            qr_img = generate_qr_code(payment_data, box_size=6)
            
            # Convert PIL image to bytes for Streamlit
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            # Display QR code with controlled width
            qr_placeholder.markdown('<div class="qr-container"></div>', unsafe_allow_html=True)
            qr_placeholder.image(byte_im, caption=f"Payment QR Code for PKR {amount:.2f}", width=300)
            
            # Display success message with data preview
            st.markdown(f'''
            <div class="success-box">
                <h3>Payment QR Code Generated Successfully!</h3>
                <p>The QR code contains the following payment information:</p>
                <ul>
                    <li><strong>Sender:</strong> {st.session_state.username}</li>
                    <li><strong>CNIC:</strong> {st.session_state.user_cnic}</li>
                    <li><strong>Amount:</strong> PKR {amount:.2f}</li>
                </ul>
                <p>You can download the QR code by right-clicking on the image and selecting "Save Image As..."</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # Display instructions if no QR code has been generated yet
        if not submitted:
            qr_placeholder.markdown('''
            <div class="info-box">
                <h3>Instructions</h3>
                <p>Enter the amount and click "Generate Payment QR Code" to create a QR code for payment.</p>
                <p>The generated QR code can be scanned by another user to make a payment to you.</p>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
   from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from pyzbar import pyzbar
import av
import cv2
import json

# Global result holder (Streamlit-webrtc limitation)
if 'qr_result' not in st.session_state:
    st.session_state.qr_result = None

# Define the QR Scanner transformer
class QRScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        barcodes = pyzbar.decode(img)
        for barcode in barcodes:
            qr_data = barcode.data.decode("utf-8")
            st.session_state.qr_result = qr_data  # Set in session state
            (x, y, w, h) = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return img

from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from pyzbar import pyzbar
import av
import cv2
import json

# Global result holder (Streamlit-webrtc limitation)
if 'qr_result' not in st.session_state:
    st.session_state.qr_result = None

# Define the QR Scanner transformer
class QRScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        barcodes = pyzbar.decode(img)
        for barcode in barcodes:
            qr_data = barcode.data.decode("utf-8")
            st.session_state.qr_result = qr_data  # Set in session state
            (x, y, w, h) = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return img

# Tab 3: Scan & Pay
with tab3:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Scan & Pay</p>', unsafe_allow_html=True)

    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False

    scan_tab1, scan_tab2 = st.tabs(["Live Camera", "Upload Image"])

    with scan_tab1:
        col1, col2 = st.columns([3, 2])

        with col1:
            if not st.session_state.camera_active:
                if st.button("🎥 Start Camera", key="start_camera"):
                    st.session_state.camera_active = True
                    st.session_state.qr_result = None
                    st.rerun()
            else:
                if st.button("⏹️ Stop Camera", key="stop_camera"):
                    st.session_state.camera_active = False
                    st.rerun()

            if st.session_state.camera_active:
                st.markdown("### 📷 Real-time QR Scanner")
                st.markdown("Point your camera at a QR code")

                ctx = webrtc_streamer(
                    key="qr",
                    video_transformer_factory=QRScanner,
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True,
                )

                if st.session_state.qr_result:
                    st.success("✅ QR Code detected!")
                    st.session_state.camera_active = False

                    try:
                        payment_data = json.loads(st.session_state.qr_result)
                        if payment_data.get("type") == "payment":
                            st.session_state.parsed_payment_data = payment_data
                            st.session_state.scan_state = "detected"
                            st.rerun()
                        else:
                            st.error("❌ Invalid QR code: Not a payment request.")
                    except Exception as e:
                        st.error(f"❌ Error: Could not parse QR code data. {str(e)}")
            else:
                st.markdown('''
                <div class="info-box">
                    <h4>📱 Camera Inactive</h4>
                    <p>Click the "Start Camera" button to begin real-time scanning.</p>
                </div>
                ''', unsafe_allow_html=True)

        with col2:
            if st.session_state.get("scan_state") == "detected" and st.session_state.get("parsed_payment_data"):
                payment_data = st.session_state.parsed_payment_data

                st.markdown(f'''
                <div class="result-text">
                    <h4>🎯 Payment Detected</h4>
                    <p><strong>Recipient:</strong> {payment_data['sender']}</p>
                    <p><strong>Amount:</strong> PKR {payment_data['amount']:.2f}</p>
                    <p><strong>Your Balance:</strong> PKR {st.session_state.balance:.2f}</p>
                </div>
                ''', unsafe_allow_html=True)
        
        # Upload Image Tab
        with scan_tab2:
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.markdown("### Upload QR Code Image")
                uploaded_file = st.file_uploader(
                    "Choose a QR code image", 
                    type=['jpg', 'jpeg', 'png', 'bmp', 'tiff'], 
                    key="qr_upload_main"
                )
            
            if uploaded_file is not None:
                # Process uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", width=300)
                
                # Convert to numpy array
                img_array = np.array(image)
                
                # Convert RGB to BGR for OpenCV
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Process button
                if st.button("🔍 Scan Uploaded Image", type="primary"):
                    with st.spinner("Processing image..."):
                        display_frame, qr_value = detect_qr_code(img_array)
                        
                        if qr_value:
                            st.success("✅ QR Code found in image!")
                            
                            # Parse the QR data
                            parsed_data, is_valid, message = parse_qr_data(qr_value)
                            
                            if is_valid:
                                st.session_state.qr_result = qr_value
                                st.session_state.parsed_payment_data = parsed_data
                                st.session_state.scan_state = "detected"
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                        else:
                            st.error("❌ No QR code detected in the uploaded image.")
        
        with col2:
            # Payment details for uploaded image
            if st.session_state.scan_state == "detected" and st.session_state.parsed_payment_data:
                payment_data = st.session_state.parsed_payment_data
                
                st.markdown(f'''
                <div class="result-text">
                    <h4>📋 Payment Details</h4>
                    <p><strong>Recipient:</strong> {payment_data['sender']}</p>
                    <p><strong>CNIC:</strong> {payment_data['sender_cnic']}</p>
                    <p><strong>Amount:</strong> PKR {payment_data['amount']:.2f}</p>
                    <p><strong>Your Balance:</strong> PKR {st.session_state.balance:.2f}</p>
                </div>
                ''', unsafe_allow_html=True)
                
                # Payment confirmation
                if st.session_state.balance >= payment_data['amount']:
                    if st.button("✅ Confirm Payment", type="primary", key="confirm_upload_payment"):
                        success, message = process_payment(
                            payment_data['amount'],
                            payment_data['sender'],
                            payment_data['sender_cnic']
                        )
                        if success:
                            st.session_state.scan_state = "confirmed"
                            st.success("🎉 Payment completed successfully!")
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.error(f"💸 Insufficient funds. Need PKR {payment_data['amount']:.2f}")
                
                if st.button("❌ Cancel Payment", key="cancel_upload_payment"):
                    st.session_state.scan_state = "idle"
                    st.session_state.parsed_payment_data = None
                    st.rerun()
            else:
                st.markdown('''
                <div class="info-box">
                    <h4>📁 Upload Scanner</h4>
                    <p>Upload an image containing a QR code to scan it.</p>
                    <p><strong>Supported formats:</strong></p>
                    <p>JPG, PNG, BMP, TIFF</p>
                </div>
                ''', unsafe_allow_html=True)
    
    # Payment success display (shown in both tabs)
    if st.session_state.scan_state == "confirmed":
        st.markdown("---")
        if st.session_state.transaction_history:
            last_transaction = st.session_state.transaction_history[-1]
            
            st.markdown(f'''
            <div class="success-box">
                <h4>🎉 Payment Successful!</h4>
                <p><strong>Amount Paid:</strong> PKR {last_transaction['amount']:.2f}</p>
                <p><strong>Recipient:</strong> {last_transaction['recipient']}</p>
                <p><strong>New Balance:</strong> PKR {last_transaction['balance_after']:.2f}</p>
                <p><strong>Transaction Time:</strong> {last_transaction['date']}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        col_reset1, col_reset2 = st.columns(2)
        with col_reset1:
            if st.button("🔄 Scan Another QR Code", key="scan_another_main"):
                st.session_state.scan_state = "idle"
                st.session_state.qr_result = None
                st.session_state.parsed_payment_data = None
                st.rerun()
        
        with col_reset2:
            if st.button("📊 View Transactions", key="view_transactions"):
                st.session_state.scan_state = "idle"
                st.session_state.qr_result = None
                st.session_state.parsed_payment_data = None
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 4: Transaction History
    with tab4:
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Transaction History</p>', unsafe_allow_html=True)
            
        if st.session_state.transaction_history:
            st.markdown(f'<div class="balance-display">Current Balance: PKR {st.session_state.balance:.2f}</div>', unsafe_allow_html=True)
            
            # Display transactions
            for i, transaction in enumerate(reversed(st.session_state.transaction_history)):
                st.markdown(f'''
                <div class="transaction-details">
                    <h4>Transaction #{len(st.session_state.transaction_history) - i}</h4>
                    <p><strong>Date:</strong> {transaction['date']}</p>
                    <p><strong>Type:</strong> {transaction['type'].title()}</p>
                    <p><strong>Amount:</strong> PKR {transaction['amount']:.2f}</p>
                    <p><strong>Recipient:</strong> {transaction['recipient']}</p>
                    <p><strong>Recipient CNIC:</strong> {transaction['recipient_cnic']}</p>
                    <p><strong>Balance After:</strong> PKR {transaction['balance_after']:.2f}</p>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="info-box">
                <h3>No Transactions Yet</h3>
                <p>Your transaction history will appear here after you make your first payment.</p>
            </div>
            ''', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>© 2025 QR Payment System | Built with Streamlit</p>", 
    unsafe_allow_html=True
)
