package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	greeting := os.Getenv("GREETING")
	if greeting == "" {
		greeting = "hello from image default"
	}
	version := os.Getenv("APP_VERSION")

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		fmt.Fprintf(w, "%s | version=%s | path=%s\n", greeting, version, r.URL.Path)
	})

	log.Printf("gateway listening on :8080 (version=%s)", version)
	log.Fatal(http.ListenAndServe(":8080", mux))
}
