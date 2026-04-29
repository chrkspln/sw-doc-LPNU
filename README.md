# Lab 4 — Strategy Pattern over the NCDC Storm Events Dataset

A Python application that reads weather-event records from the NCDC
Storm Events Database (variant 27) and pushes them to one of four
storage destinations: the console, a local file, Apache Kafka, or
Redis. Switching destinations happens entirely in `config.yaml`.

The reading code lives in `src/reader/` and knows nothing about
output. It produces an iterator of `StormEvent` objects and stops
there. The output code lives in `src/output/` and knows nothing about
input — it accepts any iterable of events. They meet in `main.py`,
which is the Strategy pattern's *Client*: it holds an
`IOutputStrategy` reference whose concrete type it never inspects.

The four sinks (console, file, Kafka, Redis) are interchangeable
because they all implement the same three-method interface
(`open` / `write` / `close`). A factory function in
`src/output/factory.py` is the only place in the codebase where the
concrete strategy classes meet a config string. Adding a fifth sink
later — S3, PostgreSQL, RabbitMQ, anything — is one new strategy
class and one new branch in the factory. Nothing else changes.

The Kafka and Redis strategies work in two modes. With
`output.dry_run: true` they print exactly what they *would* send to
the broker, without actually connecting — handy for demoing the
pattern without standing up infrastructure. Set `dry_run: false`
and they connect for real to whatever's listening on the configured
host:port.

## How to run it

Install the three dependencies:

```bash
pip install -r requirements.txt
```

(YAML for the config, plus the Kafka and Redis client libraries.
The Kafka and Redis libraries are only used when their respective
strategies are active — the console and file strategies have zero
external dependencies.)

Generate the sample dataset (200 storm events in the real NCDC
column format):

```bash
python -m scripts.generate_sample --output data/storm_events.csv --rows 200
```

Run the program with whatever strategy is currently configured in
`config.yaml`:

```bash
python -m src.main
```

To switch strategies, edit `config.yaml`:

```yaml
output:
  strategy: console     # change to: file | kafka | redis
```

Or override on the command line for a one-off run:

```bash
python -m src.main --strategy console
python -m src.main --strategy file
python -m src.main --strategy kafka     # dry-run by default
python -m src.main --strategy redis     # dry-run by default
```

## Project layout

```
lab4/
├── README.md
├── requirements.txt
├── config.yaml                       ← THE swap point — change this, not code
├── docker-compose.yml                ← optional Kafka + Redis for real runs
├── data/storm_events.csv             ← generated sample dataset
├── scripts/generate_sample.py        ← realistic NCDC-format generator
└── src/
    ├── main.py                       ← the Strategy pattern's Client
    ├── config.py                     ← thin YAML loader
    ├── reader/                       ← data-source side; no idea about output
    │   ├── interfaces.py             ← IStormEventReader
    │   ├── models.py                 ← StormEvent dataclass (NCDC schema)
    │   └── csv_reader.py             ← CsvStormEventReader implementation
    └── output/                       ← sink side; no idea where data came from
        ├── interfaces.py             ← IOutputStrategy  ← THE GoF Strategy
        ├── factory.py                ← config string → concrete strategy
        └── strategies/               ← one file per concrete sink
            ├── console.py
            ├── file.py
            ├── kafka.py
            └── redis.py
```

## How the Strategy pattern is realized in this code

The GoF book describes Strategy with three roles: a **Strategy** interface,
a set of **ConcreteStrategy** implementations, and a **Context** (sometimes
called the Client) that holds a Strategy reference and delegates to it.

The mapping:

`IOutputStrategy` in `src/output/interfaces.py` is the **Strategy** role.
It declares three methods — `open`, `write`, `close` — plus a default
`write_all` that runs the lifecycle over an iterable of events.

`ConsoleOutputStrategy`, `FileOutputStrategy`, `KafkaOutputStrategy`,
`RedisOutputStrategy` (each in its own file under `src/output/strategies/`)
are the four **ConcreteStrategy** classes. Each one knows exactly one
destination protocol — `print` to stdout, `open()` and `write()` for
files, `KafkaProducer.send()` for Kafka, `redis.rpush()`/`xadd()`/`hset()`
for Redis. They share nothing except the interface they implement.

`main.py` is the **Client/Context**. It receives a strategy from the
factory, calls `write_all()` on it, and never looks inside the object.
Crucially, the file imports `IOutputStrategy` and the factory function
— but no concrete strategy class. You can verify this by grepping
`main.py` for the four concrete strategy class names: there are zero
matches.

## Config-driven swapping

When the program starts it loads `config.yaml`, finds the
`output.strategy` field, and passes the parsed config dict to
`build_output_strategy(...)` in the factory. The factory does a tiny
match on the strategy name and returns a fully-configured concrete
instance. The rest of the program never sees the concrete type.

Walking through the swap mechanics: changing `console` to `kafka`
in the config causes the factory to instantiate `KafkaOutputStrategy`
instead of `ConsoleOutputStrategy`. The `main()` function, the reader,
the model dataclass — none of those notice. They keep calling the
same three methods on whatever object the factory returned. The
event loop in `IOutputStrategy.write_all` runs unchanged. That's
the payoff of the pattern: a behaviour change that touches only
configuration.

## Dry-run mode

The Kafka and Redis strategies each accept a `dry_run` flag in their
constructor. When true:

- `open()` prints a one-line "would connect to …" notice and skips
  the actual broker handshake. The kafka-python / redis libraries
  are never imported, so the program runs even on a machine that
  doesn't have them installed.
- `write()` prints the exact command that would be issued — the
  Kafka topic + key + JSON payload, or the Redis command
  (`RPUSH …`, `XADD …`, or `HSET …` depending on `mode`).
- `close()` reports the total count.

## Running against real Kafka and Redis

The included `docker-compose.yml` brings up a single-node Redis
and a single-node Kafka in KRaft mode (no separate Zookeeper):

```bash
docker compose up -d
```

Then in `config.yaml` set:

```yaml
output:
  strategy: redis           # or kafka
  dry_run: false
```

Run the program. For Redis you can verify the writes with
`redis-cli LLEN storm-events` (or `XLEN` if `mode: stream`).
For Kafka you can use the bundled console consumer:

```bash
docker exec -it lab4-kafka kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic storm-events --from-beginning
```

This was tested end-to-end during development — 50 sample events
written through the Redis strategy and then read back via
`redis-cli` confirmed the round trip.

