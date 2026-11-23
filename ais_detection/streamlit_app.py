import streamlit as st
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import pickle
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / 'models'

# =====================================================
# LOAD METADATA
# =====================================================
with open(MODEL_DIR / 'metadata.pkl', 'rb') as f:
    metadata = pickle.load(f)

FEATURES = metadata['features']
WINDOW_SIZE = metadata['window_size']
THRESHOLD = metadata['threshold']
HIDDEN_DIM = metadata['hidden_dim']
LATENT_DIM = metadata['latent_dim']

# =====================================================
# LOAD SCALER
# =====================================================
with open(MODEL_DIR / 'scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# =====================================================
# MODEL DEFINITION
# =====================================================
class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features, hidden_dim=32, latent_dim=16, num_layers=1):
        super().__init__()

        # Encoder
        self.encoder = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )

        self.encoder_to_latent = nn.Linear(hidden_dim, latent_dim)

        # Decoder
        self.latent_to_decoder = nn.Linear(latent_dim, hidden_dim)

        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )

        self.output_layer = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        batch_size, seq_len, _ = x.shape

        # Encode
        _, (hidden, _) = self.encoder(x)

        latent = self.encoder_to_latent(hidden[-1])

        # Prepare decoder input
        decoder_input = self.latent_to_decoder(latent)
        decoder_input = decoder_input.unsqueeze(1).repeat(1, seq_len, 1)

        # Decode
        decoded, _ = self.decoder(decoder_input)

        reconstructed = self.output_layer(decoded)

        return reconstructed

# =====================================================
# LOAD TRAINED MODEL
# =====================================================
device = torch.device('cpu')

model = LSTMAutoencoder(
    n_features=len(FEATURES),
    hidden_dim=HIDDEN_DIM,
    latent_dim=LATENT_DIM
)

model.load_state_dict(
    torch.load(MODEL_DIR / 'lstm_autoencoder.pth', map_location=device)
)

model.eval()

# =====================================================
# STREAMLIT PAGE SETTINGS
# =====================================================
st.set_page_config(
    page_title='AIS Anomaly Detection',
    page_icon='🚢',
    layout='wide'
)

st.title('🚢 AIS Anomaly Detection')
st.markdown('### Upload AIS trajectory data')

st.info(
    f'The uploaded CSV must contain at least **{WINDOW_SIZE} consecutive AIS records** '
    f'and the following columns:\\n\\n'
    f'**{", ".join(FEATURES)}**'
)

# =====================================================
# FILE UPLOAD
# =====================================================
uploaded = st.file_uploader(
    'Upload CSV',
    type=['csv']
)

if uploaded is not None:

    # Read CSV
    df = pd.read_csv(uploaded)

    st.subheader('Uploaded Data Preview')
    st.dataframe(df.head())

    # Validate columns
    missing = [c for c in FEATURES if c not in df.columns]

    if missing:
        st.error(f'❌ Missing columns: {missing}')

    # Validate minimum row count
    elif len(df) < WINDOW_SIZE:
        st.error(
            f'❌ CSV must contain at least {WINDOW_SIZE} rows. '
            f'Found {len(df)} rows.'
        )

    else:
        # =================================================
        # SLIDING WINDOW INFERENCE
        # =================================================
        data = df[FEATURES].astype(float).reset_index(drop=True)

        results = []

        for start in range(len(data) - WINDOW_SIZE + 1):

            end = start + WINDOW_SIZE

            # Extract 20-row window
            window = data.iloc[start:end].values

            # Scale
            window_scaled = scaler.transform(window)

            # Shape -> (1, 20, n_features)
            X_tensor = torch.tensor(
                window_scaled,
                dtype=torch.float32
            ).unsqueeze(0)

            # Inference
            with torch.no_grad():
                reconstruction = model(X_tensor)

                error = ((reconstruction - X_tensor) ** 2).mean().item()

            results.append({
                'window_start_row': start + 1,
                'window_end_row': end,
                'anomaly_score': error,
                'prediction': 'Anomaly' if error > THRESHOLD else 'Normal'
            })

        results_df = pd.DataFrame(results)

        # =================================================
        # SUMMARY METRICS
        # =================================================
        st.subheader('Detection Summary')

        total_windows = len(results_df)
        anomalous_windows = (results_df['prediction'] == 'Anomaly').sum()
        max_score = results_df['anomaly_score'].max()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric('Total Windows', total_windows)

        with col2:
            st.metric('Anomalous Windows', anomalous_windows)

        with col3:
            st.metric('Maximum Score', f'{max_score:.4f}')

        # Overall decision
        if anomalous_windows > 0:
            st.error('⚠️ Anomalies detected in the uploaded trajectory')
        else:
            st.success('✅ No anomalies detected')

        # =================================================
        # TOP ANOMALOUS WINDOWS
        # =================================================
        st.subheader('Top Anomalous Windows')

        top_df = results_df.sort_values(
            'anomaly_score',
            ascending=False
        ).head(10)

        st.dataframe(top_df)

        # =================================================
        # ALL WINDOW RESULTS
        # =================================================
        st.subheader('All Window Results')
        st.dataframe(results_df)

        # =================================================
        # SCORE CHART
        # =================================================
        st.subheader('Anomaly Score by Window')

        chart_df = results_df[['window_start_row', 'anomaly_score']].rename(
            columns={'window_start_row': 'Window'}
        )

        st.line_chart(chart_df.set_index('Window'))

        st.caption(
            f'Red-flag threshold used by the model: {THRESHOLD:.6f}'
        )

        # =================================================
        # DOWNLOAD RESULTS
        # =================================================
        csv = results_df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label='⬇️ Download Window-wise Results',
            data=csv,
            file_name='trajectory_window_results.csv',
            mime='text/csv'
        )

# =====================================================
# FOOTER
# =====================================================
st.markdown('---')
st.caption(
    'AIS Anomaly Detection using LSTM Autoencoder | '
    'PyTorch + Streamlit | Sliding Window Inference'
)