"""
CSV to Redpanda Producer
========================
Reads AIS data from CSV and streams to Redpanda topic 'ais_raw'.
Loops continuously when reaching end of file.
"""
import os
import json
import time
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
STREAM_INTERVAL_SECONDS = float(os.getenv('STREAM_INTERVAL_SECONDS', '2'))
CSV_PATH = os.getenv('CSV_PATH', 'data/ais_copenhagen_filtered.csv')
TOPIC_NAME = 'ais_raw'


def create_producer(max_retries=30, retry_delay=2):
    """Create Kafka producer with retries for Redpanda startup."""
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            print(f"[PRODUCER] Connected to Redpanda at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            print(f"[PRODUCER] Waiting for Redpanda... attempt {attempt + 1}/{max_retries}")
            time.sleep(retry_delay)
    
    raise RuntimeError(f"Could not connect to Redpanda after {max_retries} attempts")


def load_ais_data(csv_path):
    """Load and prepare AIS data from CSV."""
    print(f"[PRODUCER] Loading AIS data from: {csv_path}")
    
    df = pd.read_csv(csv_path, on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    
    # Standardize column names
    col_mapping = {
        '# Timestamp': 'timestamp_str',
        'Timestamp': 'timestamp_str',
        'MMSI': 'mmsi',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'SOG': 'sog',
        'COG': 'cog',
        'Heading': 'heading'
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
    
    # Select required columns
    required_cols = ['timestamp_str', 'mmsi', 'latitude', 'longitude', 'sog', 'cog', 'heading']
    for col in required_cols:
        if col not in df.columns:
            if col == 'timestamp_str':
                df[col] = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')
            else:
                df[col] = 0
    
    df = df[required_cols].dropna()
    print(f"[PRODUCER] Loaded {len(df)} AIS records")
    
    return df


def stream_ais_data():
    """Main streaming loop."""
    print("=" * 60)
    print("AIS DATA PRODUCER - Streaming to Redpanda")
    print("=" * 60)
    print(f"  Kafka Bootstrap: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  Topic: {TOPIC_NAME}")
    print(f"  Interval: {STREAM_INTERVAL_SECONDS}s")
    print(f"  CSV: {CSV_PATH}")
    print("=" * 60)
    
    producer = create_producer()
    df = load_ais_data(CSV_PATH)
    
    record_count = 0
    loop_count = 0
    
    print(f"\n[PRODUCER] Starting continuous stream...")
    
    while True:
        loop_count += 1
        print(f"\n[PRODUCER] === Loop {loop_count} ===")
        
        for idx, row in df.iterrows():
            # Build message
            message = {
                'timestamp_str': str(row['timestamp_str']),
                'mmsi': int(row['mmsi']),
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'sog': float(row['sog']),
                'cog': float(row['cog']),
                'heading': float(row['heading'])
            }
            
            # Use MMSI as key for partition ordering
            key = str(message['mmsi'])
            
            # Send to Redpanda
            future = producer.send(TOPIC_NAME, key=key, value=message)
            future.get(timeout=10)  # Wait for confirmation
            
            record_count += 1
            print(f"[{record_count}] Sent MMSI {message['mmsi']} | lat={message['latitude']:.4f}, lon={message['longitude']:.4f}, sog={message['sog']}")
            
            time.sleep(STREAM_INTERVAL_SECONDS)
        
        print(f"\n[PRODUCER] Completed loop {loop_count} ({len(df)} records). Restarting...")


if __name__ == '__main__':
    try:
        stream_ais_data()
    except KeyboardInterrupt:
        print("\n[PRODUCER] Stopped by user")
    except Exception as e:
        print(f"\n[PRODUCER] Error: {e}")
        raise
