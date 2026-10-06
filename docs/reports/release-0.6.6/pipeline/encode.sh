#!/usr/bin/env bash
# Encodes rendered frames into an HDR10 HEVC master, an SDR H.264 fallback and
# a JPEG poster. The frames are sRGB PNGs from render.mjs.
#
# Usage: encode.sh <frames-dir> <out-prefix> [poster-frame]
#   encode.sh D:/frames out/showwork-0.6.6 240
#
# HDR10: the sRGB frames map into BT.2020 primaries with the PQ (SMPTE 2084)
# curve. NPL sets the nits of sRGB white; 600 keeps text bright on HDR
# displays without clipping. Check the result with ffprobe:
# color_transfer=smpte2084, pix_fmt=yuv420p10le, codec tag hvc1.
set -euo pipefail
FRAMES="$1"; OUT="$2"; POSTER="${3:-240}"
NPL=600
FPS=60
mkdir -p "$(dirname "$OUT")"

TO_PQ="zscale=tin=iec61966-2-1:pin=bt709:t=smpte2084:p=bt2020:m=bt2020nc:r=tv:npl=${NPL},format=yuv420p10le"

ffmpeg -hide_banner -loglevel warning -stats -y -framerate "$FPS" -i "$FRAMES/f%04d.png" \
  -vf "$TO_PQ" -c:v libx265 -preset slow -crf 18 -tag:v hvc1 \
  -x265-params "hdr10=1:hdr10-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=${NPL},200" \
  -movflags +faststart -an "$OUT-hdr.mp4"

# SDR: convert with the BT.709 matrix (swscale defaults to BT.601) and write
# the BT.709 tags into the stream itself, or players read them as unknown.
TO_709="scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"

ffmpeg -hide_banner -loglevel warning -stats -y -framerate "$FPS" -i "$FRAMES/f%04d.png" \
  -vf "$TO_709" -c:v libx264 -preset slow -crf 19 \
  -x264-params "colorprim=bt709:transfer=bt709:colormatrix=bt709" \
  -movflags +faststart -an "$OUT-sdr.mp4"

ffmpeg -hide_banner -loglevel warning -y -i "$FRAMES/f$(printf %04d "$POSTER").png" -q:v 3 "$OUT-poster.jpg"
