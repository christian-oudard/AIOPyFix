import asyncio
from enum import Enum
import logging
from aiopyfix.connection import ConnectionState, MessageDirection
from aiopyfix.engine import FIXEngine
from aiopyfix.message import FIXMessage
from aiopyfix.server_connection import FIXServer


class Side(Enum):
    buy = 1
    sell = 2


class Server(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "server_example.store")
        # create a FIX Server using the FIX 4.4 standard
        self.server = FIXServer(self, "aiopyfix.FIX44")

        # we register some listeners since we want to know when the connection goes up or down
        self.server.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.server.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)

        # start our event listener indefinitely

    async def start(self, host, port, loop):
        await self.server.start(host, port, loop)

    def validateSession(self, targetCompId, senderCompId):
        logging.info("Received login request for %s / %s" % (senderCompId, targetCompId))
        return True

    async def onConnect(self, session):
        logging.info("Accepted new connection from %s" % (session.address(),))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON)
        session.addMessageHandler(self.onNewOrder, MessageDirection.INBOUND,
                                  self.server.protocol.msgtype.NEWORDERSINGLE)

    async def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(),))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON)
        session.removeMessageHandler(self.onNewOrder, MessageDirection.INBOUND,
                                     self.server.protocol.msgtype.NEWORDERSINGLE)

    async def onLogin(self, connectionHandler, msg):
        codec = connectionHandler.codec
        logging.info("[" + msg[codec.protocol.fixtags.SenderCompID] + "] <---- " + codec.protocol.msgtype.msgTypeToName(
            msg[codec.protocol.fixtags.MsgType]))

    async def onNewOrder(self, connectionHandler, request):
        codec = connectionHandler.codec
        try:
            side = Side(int(request.getField(codec.protocol.fixtags.Side)))
            logging.debug("<--- [%s] %s: %s %s %s@%s" % (
                codec.protocol.msgtype.msgTypeToName(request.getField(codec.protocol.fixtags.MsgType)),
                request.getField(codec.protocol.fixtags.ClOrdID), request.getField(codec.protocol.fixtags.Symbol),
                side.name, request.getField(codec.protocol.fixtags.OrderQty),
                request.getField(codec.protocol.fixtags.Price)))

            # respond with an ExecutionReport Ack
            msg = FIXMessage(codec.protocol.msgtype.EXECUTIONREPORT)
            msg.setField(codec.protocol.fixtags.Price, request.getField(codec.protocol.fixtags.Price))
            msg.setField(codec.protocol.fixtags.OrderQty, request.getField(codec.protocol.fixtags.OrderQty))
            msg.setField(codec.protocol.fixtags.Symbol, request.getField(codec.protocol.fixtags.OrderQty))
            msg.setField(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
            msg.setField(codec.protocol.fixtags.SecurityIDSource, "4")
            msg.setField(codec.protocol.fixtags.Symbol, request.getField(codec.protocol.fixtags.Symbol))
            msg.setField(codec.protocol.fixtags.Account, request.getField(codec.protocol.fixtags.Account))
            msg.setField(codec.protocol.fixtags.HandlInst, "1")
            msg.setField(codec.protocol.fixtags.OrdStatus, "0")
            msg.setField(codec.protocol.fixtags.ExecType, "0")
            msg.setField(codec.protocol.fixtags.LeavesQty, "0")
            msg.setField(codec.protocol.fixtags.Side, request.getField(codec.protocol.fixtags.Side))
            msg.setField(codec.protocol.fixtags.ClOrdID, request.getField(codec.protocol.fixtags.ClOrdID))
            msg.setField(codec.protocol.fixtags.Currency, request.getField(codec.protocol.fixtags.Currency))

            await connectionHandler.sendMsg(msg)
            logging.debug("---> [%s] %s: %s %s %s@%s" % (
                codec.protocol.msgtype.msgTypeToName(msg.msgType), msg.getField(codec.protocol.fixtags.ClOrdID),
                request.getField(codec.protocol.fixtags.Symbol), side.name,
                request.getField(codec.protocol.fixtags.OrderQty), request.getField(codec.protocol.fixtags.Price)))
        except Exception as e:
            msg = FIXMessage(codec.protocol.msgtype.EXECUTIONREPORT)
            msg.setField(codec.protocol.fixtags.OrdStatus, "4")
            msg.setField(codec.protocol.fixtags.ExecType, "4")
            msg.setField(codec.protocol.fixtags.LeavesQty, "0")
            msg.setField(codec.protocol.fixtags.Text, str(e))
            msg.setField(codec.protocol.fixtags.ClOrdID, request.getField(codec.protocol.fixtags.ClOrdID))

            await connectionHandler.sendMsg(msg)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    server = Server()
    loop.run_until_complete(server.start('', 9898, loop))
    loop.run_forever()
