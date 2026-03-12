"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import requests
import config
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            """
            GET my-api-gateway-address/order/{id} ...
            """
            response = requests.get(f'{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}',
                headers={'Content-Type': 'application/json'}
            )
            data = response.json()
            user_id = data['user_id'] if data else 0
            total_amount = data['total_amount'] if data else 0
            
            """
            POST my-api-gateway-address/payments ...
            json={ voir collection Postman pour en savoir plus ... }
            """
            response = requests.post(f'{config.API_GATEWAY_URL}/payments-api/payments',
                json={
                    "user_id": user_id,
                    "order_id": self.order_id,
                    "total_amount": total_amount
                },
                headers={'Content-Type': 'application/json'}
            )
            if response.ok:
                self.logger.debug("Transition d'état: CreatePayment -> PAYMENT_CREATED")
                return OrderSagaState.PAYMENT_CREATED
            else:
                return self.rollback()

        except Exception:
            return self.rollback()
        
    def rollback(self):
        """ Call StoreManager to restore stock quantities if payment transaction creation fails """
        response = requests.put(f'{config.API_GATEWAY_URL}/store-manager-api/orders',
                json={
                    "items": self.order_data['items'],
                    "operation": "+"
                },
                headers={'Content-Type': 'application/json'}
            )
        self.logger.debug("Transition d'état: CreatePaymentFailure -> STOCK_INCREASED")
        return OrderSagaState.STOCK_INCREASED