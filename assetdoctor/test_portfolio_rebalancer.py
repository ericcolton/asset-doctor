#!/usr/bin/env python3

from .price_lookup import PriceLookup
from .portfolio import Portfolio, Position
from .model_portfolio_builder import ModelPortfolioBuilder, ModelPosition
from .portfolio_rebalancer import PortfolioRebalancer, RebalanceOptions, RoundingBehavior, TransactionType

def __default_setup(target_total: float):
    options = RebalanceOptions(
        target_total_value=target_total,
        allow_share_exchanges=False,
        allow_fractional_shares=False,
        rounding_behavior=RoundingBehavior.NEAREST)
    
    prices = PriceLookup()
    prices.add_price('AAA', 100)
    prices.add_price('BBB', 200)

    model_builder = ModelPortfolioBuilder(options.target_total_value, prices)
    model_builder.add_model_position(ModelPosition('AAA', 50))
    model_builder.add_model_position(ModelPosition('BBB', 50))
    model = model_builder.generate_model_portfolio()

    return options, prices, model

def test_no_rebalance_needed():

    options, prices, model = __default_setup(4000)

    live = Portfolio()
    live.add_position(Position('AAA', 20))
    live.add_position(Position('BBB', 10))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 0

def test_new_portfolio():

    options, prices, model = __default_setup(4000)

    live = Portfolio()
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 2

    aaa = next(filter(lambda x: x.ticker == 'AAA', instructions), None)
    bbb = next(filter(lambda x: x.ticker == 'BBB', instructions), None)

    assert aaa.transaction_type == TransactionType.BUY and aaa.quantity == 20
    assert bbb.transaction_type == TransactionType.BUY and bbb.quantity == 10

def test_simple_rebalance(): 

    options, prices, model = __default_setup(4000)

    live = Portfolio()
    live.add_position(Position('AAA', 15))
    live.add_position(Position('BBB', 15))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 2

    buy = next(filter(lambda x: x.transaction_type == TransactionType.BUY, instructions), None)
    sell = next(filter(lambda x: x.transaction_type == TransactionType.SELL, instructions), None)
    assert buy.ticker == 'AAA' and buy.quantity == 5
    assert sell.ticker == 'BBB' and sell.quantity == 5

def test_low_drift_doesnt_trigger_rebalance():

    options, prices, model = __default_setup(3900)

    live = Portfolio()
    live.add_position(Position('AAA', 19))
    live.add_position(Position('BBB', 10))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 0

def test_low_drift_does_trigger_when_fractional_allowed():

    target_total = 3900
    _, prices, model = __default_setup(target_total)
    options = RebalanceOptions(
        target_total_value=target_total,
        allow_share_exchanges=False,
        allow_fractional_shares=True,
        rounding_behavior=RoundingBehavior.NEAREST)

    live = Portfolio()
    live.add_position(Position('AAA', 19))
    live.add_position(Position('BBB', 10))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 2

    buy = next(filter(lambda x: x.transaction_type == TransactionType.BUY, instructions), None)
    sell = next(filter(lambda x: x.transaction_type == TransactionType.SELL, instructions), None)
    assert buy.ticker == 'AAA' and buy.quantity == 0.5
    assert sell.ticker == 'BBB' and sell.quantity == 0.25

def test_low_drift_does_trigger_when_rounding_up():

    target_total = 3900
    _, prices, model = __default_setup(target_total)
    options = RebalanceOptions(
        target_total_value=target_total,
        allow_share_exchanges=False,
        allow_fractional_shares=False,
        rounding_behavior=RoundingBehavior.UP)

    live = Portfolio()
    live.add_position(Position('AAA', 19))
    live.add_position(Position('BBB', 10))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 1

    buy = instructions[0]
    assert buy.ticker == 'AAA' and buy.transaction_type == TransactionType.BUY and buy.quantity == 1

def test_exchange_allowed():

    target_total = 3900
    _, prices, model = __default_setup(target_total)
    options = RebalanceOptions(
        target_total_value=target_total,
        allow_share_exchanges=True,
        allow_fractional_shares=True,
        rounding_behavior=RoundingBehavior.NEAREST)

    live = Portfolio()
    live.add_position(Position('AAA', 19))
    live.add_position(Position('BBB', 10))
    
    rebalancer = PortfolioRebalancer(prices, options)
    rebalancer.set_model_portfolio(model)
    rebalancer.set_live_portfolio(live)
    instructions = rebalancer.build_rebalance_instructions()
    assert len(instructions) == 1

    exchange = next(filter(lambda x: x.transaction_type == TransactionType.EXCHANGE, instructions), None)
    assert exchange.ticker == 'BBB' and exchange.quantity == 0.25
    assert exchange.counter_ticker == 'AAA' and exchange.counter_quantity == 0.5

