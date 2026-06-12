package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_3_2Test {

    @Test
    void testReadAgain_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -2); // Set to UNDEFINED
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(-2, result);
    }

    @Test
    void testReadAgain_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 116); // Set lastChar to 't'
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(116, result);
    }

    @Test
    void testReadAgain_afterEndOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -1); // Set to END_OF_STREAM
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(-1, result);
    }
    
    @Test
    void testRead_singleCharacter() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("a"));
        int result = reader.read();
        Assertions.assertEquals('a', result);
    }

    @Test
    void testRead_multipleCharacters() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("abc"));
        char[] buffer = new char[3];
        int result = reader.read(buffer, 0, 3);
        Assertions.assertEquals(3, result);
        Assertions.assertArrayEquals(new char[] {'a', 'b', 'c'}, buffer);
    }

    @Test
    void testReadLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Hello World\nThis is a test"));
        String line = reader.readLine();
        Assertions.assertEquals("Hello World", line);
    }

    @Test
    void testLookAhead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Hello"));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 'H'); // Set lastChar to 'H'
        
        int result = reader.lookAhead();
        
        Assertions.assertEquals('H', result);
    }

    @Test
    void testGetLineNumber() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));
        reader.readLine(); // Read first line
        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(1, lineNumber);
    }
}