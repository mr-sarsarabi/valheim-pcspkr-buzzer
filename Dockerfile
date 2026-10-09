FROM alpine:3.20

# Install python3 and yaml without needing build tools
RUN apk add --no-cache python3 py3-yaml

WORKDIR /app

COPY driver.py sound_packs.py valheim_parser.py main.py config.yaml /app/

CMD ["python3", "-u", "main.py"]
