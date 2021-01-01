package websocket

import (
	"log"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type conn struct {
	wsConn *websocket.Conn
	send   chan []byte
	wg     sync.WaitGroup
}

func newConn(wsConn *websocket.Conn) *conn {
	return &conn{
		wsConn: wsConn,
		send:   make(chan []byte),
	}
}

func (c *conn) run() {
	c.wg.Add(2)
	go c.readPump()
	go c.writePump()
}

func (c *conn) readPump() {
	defer c.wg.Done()

	c.wsConn.SetReadLimit(maxMessageSize)
	c.wsConn.SetReadDeadline(time.Now().Add(readTimeout))
	c.wsConn.SetPongHandler(func(string) error {
		c.wsConn.SetReadDeadline(time.Now().Add(readTimeout))
		return nil
	})

	for {
		typ, msg, err := c.wsConn.ReadMessage()
		if err != nil {
			log.Println("err reading:", err)
			close(c.send)
			return
		}

		if typ != websocket.TextMessage {
			continue
		}

		c.send <- msg
	}
}

func (c *conn) writePump() {
	defer c.wg.Done()

	ticker := time.NewTicker(pingPeriod)
	defer ticker.stop()

	for s := range c.send {
		if err := c.wsConn.WriteMessage(websocket.TextMessage, s); err != nil {
			log.Println("err write:", err)
			return
		}
	}
}
