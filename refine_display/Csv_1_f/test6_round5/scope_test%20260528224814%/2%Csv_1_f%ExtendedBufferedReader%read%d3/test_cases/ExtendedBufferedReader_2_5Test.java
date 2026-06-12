package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.StringReader;

class ExtendedBufferedReader_2_5Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader(""));
    }

    @Test
    void testRead_normalCase() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("Hello\nWorld"));
        Assertions.assertEquals('H', reader.read());
        Assertions.assertEquals('e', reader.read());
        Assertions.assertEquals('l', reader.read());
        Assertions.assertEquals('l', reader.read());
        Assertions.assertEquals('o', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('W', reader.read());
        Assertions.assertEquals('o', reader.read());
        Assertions.assertEquals('r', reader.read());
        Assertions.assertEquals('l', reader.read());
        Assertions.assertEquals('d', reader.read());
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_newLineHandling() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("Line1\rLine2\nLine3\r\n"));
        Assertions.assertEquals('L', reader.read());
        Assertions.assertEquals('i', reader.read());
        Assertions.assertEquals('n', reader.read());
        Assertions.assertEquals('e', reader.read());
        Assertions.assertEquals('1', reader.read());
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals('L', reader.read());
        Assertions.assertEquals('i', reader.read());
        Assertions.assertEquals('n', reader.read());
        Assertions.assertEquals('e', reader.read());
        Assertions.assertEquals('2', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('L', reader.read());
        Assertions.assertEquals('i', reader.read());
        Assertions.assertEquals('n', reader.read());
        Assertions.assertEquals('e', reader.read());
        Assertions.assertEquals('3', reader.read());
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_endOfStream() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader(""));
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_multipleNewLines() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("\n\n\n"));
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("\r\n"));
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_charactersWithLineBreaks() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("A\rB\nC\r\nD"));
        Assertions.assertEquals('A', reader.read());
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals('B', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('C', reader.read());
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals('D', reader.read());
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }
}