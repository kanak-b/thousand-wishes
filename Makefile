list_kafka_topics: 
	docker exec -it kafka kafka-topics.sh --list --bootstrap-server kafka:9092

create_topic:
	docker exec -it kafka kafka-topics.sh --create \
	--topic $(TOPIC) \
	--bootstrap-server kafka:9092 \
	--partitions $(or $(PARTITIONS),1) \
	--replication-factor $(or $(REPLICATION),1)

describe_topic:
	docker exec -it kafka kafka-topics.sh --describe --topic $(TOPIC) --bootstrap-server kafka:9092

delete_topic:
	docker exec -it kafka kafka-topics.sh --delete --topic $(TOPIC) --bootstrap-server kafka:9092

subscribe_topic:
	docker exec -it kafka kafka-console-consumer.sh \
	--bootstrap-server kafka:9092 \
	--topic $(TOPIC) \
	--from-beginning

publish_to_topic:
	docker exec -it kafka kafka-console-producer.sh \
	--bootstrap-server kafka:9092 \
	--topic $(TOPIC)

submit-consumer_job:
	docker exec spark-master spark-submit /opt/bitnami/spark/thousand-wishes/kafka-consumer.py

submit-parquet_reader_job:
	docker exec spark-master spark-submit /opt/bitnami/spark/thousand-wishes/parquet-reader.py
