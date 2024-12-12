GRAPH_ARGS = -s $(or KRW-$(COIN),KRW-BTC) -t $(or $(TIMEFRAME),15m:60:60)

.PHONY: graph
graph:
	poetry run python graph.py $(GRAPH_ARGS)

.PHONY: price_stock
price_stock:
	poetry run python price_stock.py

.PHONY: price
price:
	poetry run python price.py