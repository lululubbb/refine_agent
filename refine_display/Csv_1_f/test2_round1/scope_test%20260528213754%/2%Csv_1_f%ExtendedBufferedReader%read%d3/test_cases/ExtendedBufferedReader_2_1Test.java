package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class ExtendedBufferedReader_2_1Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        String input = "First line\nSecond line\rThird line";
        Reader stringReader = new StringReader(input);
        reader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        assertEquals('F', reader.read());
        assertEquals('i', reader.read());
        assertEquals('r', reader.read());
        assertEquals('s', reader.read());
        assertEquals('t', reader.read());
        assertEquals(' ', reader.read());
        assertEquals('l', reader.read());
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals('\n', reader.read());
    }

    @Test
    void testRead_lineCounterIncrement() throws Exception {
        reader.read(); // Read 'F'
        reader.read(); // Read 'i'
        reader.read(); // Read 'r'
        reader.read(); // Read 's'
        reader.read(); // Read 't'
        reader.read(); // Read ' '
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '\n'
        
        assertEquals(1, getLineCounter(reader));

        reader.read(); // Read 'S'
        reader.read(); // Read 'e'
        reader.read(); // Read 'c'
        reader.read(); // Read 'o'
        reader.read(); // Read 'n'
        reader.read(); // Read 'd'
        reader.read(); // Read ' '
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '\r'
        
        assertEquals(2, getLineCounter(reader));
        reader.read(); // Read 'T'
        reader.read(); // Read 'h'
        reader.read(); // Read 'i'
        reader.read(); // Read 'r'
        reader.read(); // Read 'd'
        reader.read(); // Read ' '
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        
        assertEquals(3, getLineCounter(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {}
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_exceptionHandling() throws Exception {
        Reader faultyReader = Mockito.mock(Reader.class);
        Mockito.when(faultyReader.read()).thenThrow(new IOException("Read error"));
        ExtendedBufferedReader faultyExtendedBufferedReader = new ExtendedBufferedReader(faultyReader);
        
        assertThrows(IOException.class, faultyExtendedBufferedReader::read);
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}