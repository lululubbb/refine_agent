package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_3Test {

    @Test
    void testRead_normalCase() throws Exception {
        Reader stringReader = new StringReader("Hello\nWorld");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);
        
        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
        
        int thirdChar = reader.read();
        Assertions.assertEquals('l', thirdChar);
        
        int fourthChar = reader.read();
        Assertions.assertEquals('l', fourthChar);
        
        int fifthChar = reader.read();
        Assertions.assertEquals('o', fifthChar);
        
        int sixthChar = reader.read();
        Assertions.assertEquals('\n', sixthChar);
    }

    @Test
    void testRead_lineCounterIncrement() throws Exception {
        Reader stringReader = new StringReader("First Line\nSecond Line");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        reader.read(); // Read 'F'
        reader.read(); // Read 'i'
        reader.read(); // Read 'r'
        reader.read(); // Read 's'
        reader.read(); // Read 't'
        reader.read(); // Read ' '
        reader.read(); // Read 'L'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        Assertions.assertEquals(0, getLineNumber(reader)); // Line counter should be 0
        
        reader.read(); // Read '\n'
        Assertions.assertEquals(1, getLineNumber(reader)); // Line counter should be 1
        
        reader.read(); // Read 'S'
        reader.read(); // Read 'e'
        reader.read(); // Read 'c'
        reader.read(); // Read 'o'
        reader.read(); // Read 'n'
        reader.read(); // Read 'd'
        reader.read(); // Read ' '
        reader.read(); // Read 'L'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        Assertions.assertEquals(1, getLineNumber(reader)); // Line counter should still be 1
    }

    @Test
    void testRead_endOfStream() throws Exception {
        Reader stringReader = new StringReader("");
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        int result = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int getLineNumber(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return field.getInt(reader);
    }
}