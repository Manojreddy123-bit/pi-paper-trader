CASH0 = 100_000    # starting virtual cash, Rs
MAX_POS = 8        # max holdings
MAX_W = 0.12       # max 12% of portfolio per stock
STOP = 0.08        # sell if close falls 8% below entry
COST = 0.002       # ~0.2% per side: brokerage + taxes + slippage (approximation)
THRESH = 0.52      # ML buy threshold on predicted probability
