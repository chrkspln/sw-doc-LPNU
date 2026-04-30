# Lab 4 — Strategy Pattern over the NCDC Storm Events Dataset

A Python application that reads weather-event records from the NCDC
Storm Events Database (variant 27) and writes them to one of three
storage destinations: the console, Apache Kafka, or Redis. Switching
destinations happens entirely in `config.yaml` — no code changes.

## What the lab requires

1. Read data from the variant dataset and write it to a file.
2. Use the Strategy pattern to swap output destinations.
3. The reading code must be separated from the output code.
4. The console output must be organised using the Strategy pattern, and
   must allow switching to Kafka or Redis with minimal changes — through
   configuration files, not code edits.

## How those requirements map to the code

**Reading is in `src/reader/`.** It produces an iterator of `StormEvent`
objects from a real NCDC bulk CSV (the same `.csv.gz` files NCEI publishes
monthly) and stops there. It has no imports from `src/output/`.

**Writing is in `src/output/`.** `IOutputStrategy` is the abstract role.
`ConsoleOutputStrategy`, `KafkaOutputStrategy`, and `RedisOutputStrategy`
are the three concrete implementations. They share nothing except the
interface they implement, and they have no imports from `src/reader/`.

**`src/main.py` is the Client.** It loads `config.yaml`, asks the factory
for a strategy by name, and calls `write_all` on whatever object it
gets back. It never imports any concrete strategy class.

**Switching happens in `config.yaml`.** Edit `output.strategy` from
`console` to `kafka` or `redis`. The factory in `src/output/factory.py`
is the one place where the config string meets the concrete classes.

There are no CLI flags that override the config. The only way to swap
strategies is to edit the config file, because that's what the lab asks
for.

## How to run it

```bash
pip install -r requirements.txt
python -m src.main
```

The bundled `data/sample.csv.gz` is a 5-row file in real NCDC bulk format
(same 51 columns, same `MM/DD/YYYY hh:mm:ss` datetime format) — it lets
you exercise the pipeline offline.

To run against a real NCDC file:

```bash
python -m scripts.download_ncdc --year 2024
# Edit config.yaml: set input.file to the downloaded path.
python -m src.main
```

To switch the output destination, edit `config.yaml`:

```yaml
output:
  strategy: console     # or: kafka | redis
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
- **ConcreteStrategy:** `ConsoleOutputStrategy`, `KafkaOutputStrategy`,
  `RedisOutputStrategy`. Each knows exactly one destination protocol.
- **Client:** `main()` in `src/main.py`. Holds an `IOutputStrategy`
  reference, never inspects the concrete type. You can verify by grepping
  `main.py` for the concrete class names — there are zero matches.

## Real Kafka and Redis

The Kafka and Redis strategies are real client code — `KafkaProducer.send()`
and `redis.rpush()` respectively. To run against real services you need a
broker reachable on the configured host:port. Locally:

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

## Defence Q&A

*"Where exactly is the Strategy pattern?"* — `IOutputStrategy` in
`src/output/interfaces.py` is the abstract Strategy role; the three
concrete classes in `src/output/strategies/` implement it; `main()`
in `src/main.py` is the Client that holds an `IOutputStrategy`
reference without knowing the concrete type.

*"How do you switch from console to Kafka?"* — Edit
`output.strategy: console` to `output.strategy: kafka` in `config.yaml`.
Re-run. No code changes.

*"What does the reader know about the output?"* — Nothing.
`src/reader/` has no imports from `src/output/`.

*"How would you add PostgreSQL as a fourth destination?"* — Three
changes: write `PostgresOutputStrategy` implementing `IOutputStrategy`,
add a branch in `factory.py`, add a `postgres:` block in `config.yaml`.
Nothing else changes.

*"Why three lifecycle methods instead of one `write_all`?"* — Real sinks
have setup/teardown (Kafka producer, Redis connection, file handle).
Splitting `open` / `write` / `close` makes the lifecycle explicit. The
default `write_all` wrapper exists for callers that just want one call.
