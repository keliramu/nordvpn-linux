package response

import (
	"crypto/rsa"
	"log"
	"net/http"
	"strconv"
	"testing"
	"time"

	"github.com/NordSecurity/nordvpn-linux/test/category"
	"github.com/NordSecurity/nordvpn-linux/test/mock"

	"github.com/stretchr/testify/assert"
	"golang.org/x/crypto/ssh"
)

var privateKey *rsa.PrivateKey
var publicKey ssh.PublicKey

func TestMain(m *testing.M) {
	var err error
	privateKey, publicKey, err = mock.GenerateKeyPair()
	if err != nil {
		log.Fatalf("error on test main: %+v", err)
	}
	m.Run()
}

func TestGetSHA256Hash(t *testing.T) {
	category.Set(t, category.Unit)

	tests := []string{
		"", // empty string
		"something short",
		`something longer than 64 chars
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`,
	}
	prevHash := ""
	for _, test := range tests {
		hash := getSHA256Hash([]byte(test))
		assert.Equal(t, 64, len(hash))
		assert.NotEqual(t, prevHash, hash)
	}
}

func TestGetHashFunction(t *testing.T) {
	category.Set(t, category.Unit)

	seed := []byte("some_text")
	tests := []struct {
		name string
		f    bool
		res  []byte // use result instead of function, because it is impossible to compare 2 functions
	}{
		{name: "sha256", f: true, res: getSHA256Hash(seed)},
		{name: "md5", f: false, res: nil},
		{name: "sha512", f: false, res: nil},
		{name: "sha1", f: false, res: nil},
		{name: "invalid", f: false, res: nil},
	}
	for _, test := range tests {
		f := getHashFunction(test.name)
		assert.True(t, test.f == (f != nil), f)
		if test.f {
			assert.Equal(t, test.res, f(seed))
		}
	}
}

func TestGetSignAlgoName(t *testing.T) {
	category.Set(t, category.Unit)

	tests := []struct {
		input  string
		output string
	}{
		{input: "rsa-sha256", output: ssh.SigAlgoRSASHA2256},
		{input: "rsa-md5", output: ""},
		{input: "invalid", output: ""},
	}
	for _, test := range tests {
		res := getSignAlgoName(test.input)
		assert.Equal(t, test.output, res)
	}
}

func TestParseKeyVal(t *testing.T) {
	category.Set(t, category.Unit)

	tests := []struct {
		input string
		res   map[string]string
		error bool
	}{
		{input: "", res: nil, error: true},
		{input: "key1:invalid key2:format", res: nil, error: true},
		{input: "foo=bar", res: map[string]string{"foo": "bar"}, error: false},
		{input: "foo1=bar1,foo2=bar2", res: map[string]string{"foo1": "bar1", "foo2": "bar2"}, error: false},
	}
	for _, test := range tests {
		res, err := parseKeyVal(test.input)
		assert.True(t, test.error == (err != nil), err)
		assert.Equal(t, test.res, res)
	}
}

func setHeader(headers http.Header, key string, value string) http.Header {
	headers.Set(key, value)
	return headers
}

func validHeaders(data []byte) http.Header {
	headers, err := mock.GenerateValidHeaders(privateKey, data)
	if err != nil {
		log.Fatalf("error on generating headers: %+v", err)
	}
	return headers
}

func TestNordValidator_Validate(t *testing.T) {
	category.Set(t, category.Unit)
	sampleData := []byte(`"foo": "bar"`)
	tests := []struct {
		headers http.Header
		data    []byte
		code    int
		error   bool
	}{
		{code: 200, data: sampleData, headers: validHeaders(sampleData), error: false},
		{code: 429, data: sampleData, headers: validHeaders(sampleData), error: false},
		// Errors are OK with empty body
		{code: 404, data: sampleData, headers: validHeaders([]byte{}), error: false},
		// Success responses are NOT OK with empty body
		{code: 200, data: sampleData, headers: validHeaders([]byte{}), error: true},
		// Errors are also OK with valid actual data
		{code: 404, data: sampleData, headers: validHeaders(sampleData), error: false},
		{code: 200, data: sampleData, headers: nil, error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", ""), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Accept-Before", ""), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Digest", ""), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Signature", ""), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", "invalid_format"), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", `algorithm="sha256"`), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", `algorithm="rsa-invalid"`), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", `algorithm="invalid-sha256"`), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Digest", "invalid"), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Accept-Before", "invalid"), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData),
			"X-Accept-Before", strconv.FormatInt(time.Now().Add(-time.Second).Unix(), 10)), error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Authorization", `algorithm="rsa-sha256",key-id="invalid"`),
			error: true},
		{code: 200, data: sampleData, headers: setHeader(validHeaders(sampleData), "X-Signature", "invalid"), error: true},
	}
	for i, test := range tests {
		t.Run(strconv.Itoa(i), func(t *testing.T) {
			validator := NewNordValidator(mock.PKVault{PublicKey: publicKey})
			err := validator.Validate(test.code, test.headers, test.data)
			assert.True(t, test.error == (err != nil), err)
		})
	}
}
