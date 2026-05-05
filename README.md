# Lab 4 — Strategy Pattern over the NCDC Storm Events Dataset

A Python application that reads weather-event records from the NCDC
Storm Events Database (variant 27) and writes them to a file by default,
with the option to swap the output destination to the console, Apache
Kafka, or Redis. Switching destinations happens entirely in `config.yaml`
— no code changes.

1. **"Read data from the variant dataset and write it to a file."** —
   This is the base task. The default strategy in `config.yaml` is
   `file`, which writes events as JSON lines to `data/output.jsonl`.
2. **"Apply the Strategy pattern for output to different storages."** —
   `IOutputStrategy` is the abstract role; `FileOutputStrategy`,
   `ConsoleOutputStrategy`, `KafkaOutputStrategy`, and
   `RedisOutputStrategy` are the concrete implementations.
3. **"The console-output code must be separated from the file-reading
   code."** — `src/reader/` produces `StormEvent` objects and has zero
   imports from `src/output/`. The two sides meet only in `main.py`.
4. **"The console output must be organised using the Strategy pattern,
   and must allow switching to Kafka or Redis with minimal changes —
   through configuration files, not code edits."** — `output.strategy`
   in `config.yaml` is the single swap point. There are no CLI flags
   that override it.

## How to run it

```bash
pip install -r requirements.txt
python -m src.main
```

By default this reads `data/sample.csv.gz` (a 5-row file in real NCDC
bulk format) and writes `data/output.jsonl`.

To run against a real NCDC file:

```bash
python -m scripts.download_ncdc --year 2024
# Edit config.yaml: set input.file to the downloaded path.
python -m src.main
```

To switch the output destination, edit `config.yaml`:

```yaml
output:
  strategy: file        # or: console | kafka | redis
```

Re-run `python -m src.main`. No code edits.

## Project layout

```
lab4/
├── README.md
├── requirements.txt
├── config.yaml                       ← THE swap point
├── data/
│   ├── sample.csv                    ← 5-row test file (real NCDC schema)
│   └── sample.csv.gz                 ← same file gzipped
├── scripts/
│   └── download_ncdc.py              ← fetches real NCDC bulk files
└── src/
    ├── main.py                       ← the Strategy pattern's Client
    ├── config.py                     ← YAML loader
    ├── reader/                       ← data-source side
    │   ├── interfaces.py             ← IStormEventReader
    │   ├── models.py                 ← StormEvent dataclass (51 columns)
    │   └── csv_reader.py             ← CsvStormEventReader (gzip-aware)
    └── output/                       ← sink side
        ├── interfaces.py             ← IOutputStrategy ← THE GoF Strategy
        ├── factory.py                ← config string → concrete strategy
        └── strategies/
            ├── file.py               ← default per spec
            ├── console.py
            ├── kafka.py
            └── redis.py
```

## The Strategy pattern in this code

The GoF book describes Strategy with three roles: a Strategy interface,
concrete implementations, and a Client that holds a Strategy reference
and delegates to it.

- **Strategy:** `IOutputStrategy` in `src/output/interfaces.py`. Three
  methods: `open` / `write` / `close`, plus a default `write_all` that
  runs the lifecycle over an iterable.
- **ConcreteStrategy:** `FileOutputStrategy`, `ConsoleOutputStrategy`,
  `KafkaOutputStrategy`, `RedisOutputStrategy`. Each knows exactly one
  destination protocol.
- **Client:** `main()` in `src/main.py`. Holds an `IOutputStrategy`
  reference, never inspects the concrete type. You can verify by
  grepping `main.py` for the concrete class names — there are zero
  matches.

## Kafka and Redis

The Kafka and Redis strategies are real client code — `KafkaProducer.send()`
and `redis.rpush()` respectively. To run against real services you need
a broker reachable on the configured host:port:

```bash
# Redis
redis-server --daemonize yes --port 6379

# Kafka (single-node KRaft mode via Docker)
docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_CFG_NODE_ID=0 \
  -e KAFKA_CFG_PROCESS_ROLES=controller,broker \
  -e KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093 \
  -e KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093 \
  -e KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  -e KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT \
  -e KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
  bitnami/kafka:3.7
```

Then in `config.yaml` set `output.strategy: redis` (or `kafka`) and run.

