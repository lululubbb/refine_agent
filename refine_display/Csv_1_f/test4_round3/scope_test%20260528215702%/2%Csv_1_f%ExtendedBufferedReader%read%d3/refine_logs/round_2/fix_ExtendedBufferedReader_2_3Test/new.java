package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_3Test {

    @Test
    void testRead_normalCase() throws Exception {
        Reader stringReader = new StringReader("Hello\nWorld");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
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
    void testRead_lineCounterIncrement() throws Exception {
        Reader stringReader = new StringReader("First Line\nSecond Line");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        for (int i = 0; i < 10; i++) {
            reader.read(); // Read each character of "First Line"
        }
        Assertions.assertEquals(0, getLineNumber(reader)); // Line counter should be 0
        
        reader.read(); // Read '\n'
        Assertions.assertEquals(1, getLineNumber(reader)); // Line counter should be 1
        
        for (int i = 0; i < 11; i++) {
            reader.read(); // Read each character of "Second Line"
        }
        Assertions.assertEquals(1, getLineNumber(reader)); // Line counter should still be 1
    }

    @Test
    void testRead_endOfStream() throws Exception {
        Reader stringReader = new StringReader("");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_boundaryConditions() throws Exception {
        Reader stringReader = new StringReader("\n\r");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        Assertions.assertEquals('\n', reader.read());
        Assertions.assertEquals(0, getLineNumber(reader)); // Line counter should be 0
        
        Assertions.assertEquals('\r', reader.read());
        Assertions.assertEquals(1, getLineNumber(reader)); // Line counter should be 1
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    private int getLineNumber(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return field.getInt(reader);
    }
}