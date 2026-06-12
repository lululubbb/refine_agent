package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_4Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);
        
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Hello\nWorld", new String(buffer, 0, len));
        Assertions.assertEquals(2, getLineCounter(reader));
    }

    @Test
    void testRead_zeroLength() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Test"));
        int len = reader.read(new char[10], 0, 0);
        
        Assertions.assertEquals(0, len);
        Assertions.assertEquals(0, getLineCounter(reader));
    }

    @Test
    void testRead_noNewLine() throws Exception {
        String input = "HelloWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);
        
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("HelloWorld", new String(buffer, 0, len));
        Assertions.assertEquals(0, getLineCounter(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];
        reader.read(buffer, 0, 10); // read first part
        int len = reader.read(buffer, 0, 10); // read again
        
        Assertions.assertEquals(-1, len);
        Assertions.assertEquals(2, getLineCounter(reader));
    }

    @Test
    void testRead_mixedLineEndings() throws Exception {
        String input = "Line1\rLine2\nLine3\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[30];
        reader.read(buffer, 0, 30);
        
        Assertions.assertEquals(30, reader.read(buffer, 0, 30));
        Assertions.assertEquals(3, getLineCounter(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}