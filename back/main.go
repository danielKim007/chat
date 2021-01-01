package main

import (
	"log"
	"net/http"

	"github.com/danielKim007/chat/back/websocket"
)

func main() {
	if err := http.ListenAndServe(":8080", websocket.Handler()); err != nil {
		log.Fatalln(err)
	}
}
