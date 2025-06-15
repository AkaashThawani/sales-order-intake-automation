EMAIL_SAMPLES = {
    "scenario_1_simple_and_vague": """
    From: Alex <alex@clientcorp.com>
    To: Logistics Team <logistics@mycompany.com>
    Subject: Quick question

    Hey team,

    Can you check on our usual order? We need more of the blue things. Probably the standard amount.

    Thanks,
    Alex
    """,

    "scenario_2_multi_product_and_uncertainty": """
    From: Sarah <sarah@innovate.io>
    To: Logistics Team <logistics@mycompany.com>
    Subject: Following up

    Hi there,

    Following up on my call with Bob. He mentioned we need to restock.

    I think he said we're low on the big green gadgets, maybe get another 40 or so? Also, that last batch of yellow devices went fast, we probably should get more. Let's do a full re-order on those.

    Let me know.

    -S
    """,

    "scenario_3_email_chain_with_corrections": """
    From: Logistics Team <logistics@mycompany.com>
    To: Mark <mark@techsolutions.com>
    Subject: Re: Urgent Order

    Hi Mark, confirming your request for 100 Red Widgets.

    > From: Mark <mark@techsolutions.com>
    > To: Logistics Team <logistics@mycompany.com>
    >
    > We need widgets URGENTLY. The red ones. Get me a hundred.

    ---
    From: Mark <mark@techsolutions.com>
    To: Logistics Team <logistics@mycompany.com>
    Subject: Re: Re: Urgent Order

    Whoops, my mistake. I meant the BLUE widgets. Not the red ones. Still need 100. Sorry for the confusion!

    Please confirm.
    Mark
    """,
    
    "scenario_4_no_quantities_and_new_item": """
    From: Jenny <jenny@globaltraders.net>
    To: Logistics Team <logistics@mycompany.com>
    Subject: stock levels

    Hi,

    Can you do a stock check for me? I need to know what we have for the small steel screws. Also, we're totally out of the red widgets, we need to fix that.

    Also, I heard a rumor we might start stocking 'heavy-duty brackets'. Is that true? If so, get me a quote for a starting inventory of 200.

    Jenny
    """
}

# The LLM will need to infer "standard amount" or "full re-order".
# For this, we can define what those mean in our system.
# The LLM prompt can be told to use these defaults if a quantity is missing.
# DEFAULT_QUANTITIES = {
#     "standard amount": 100,
#     "full re-order": 50,
#     "fix that": 50, # For "we're totally out..., we need to fix that"
#     "get more": 25
# }