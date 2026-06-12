package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_3Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        char[] buf = new char[10];
        
        int len = ebr.read(buf, 0, 10);
        
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Hello\nWorl", new String(buf, 0, len));
        Assertions.assertEquals(1, getLineCounter(ebr));
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        Reader reader = new StringReader("Hello");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        char[] buf = new char[0];
        
        int len = ebr.read(buf, 0, 0);
        
        Assertions.assertEquals(0, len);
        Assertions.assertEquals(0, getLineCounter(ebr));
    }

    @Test
    void testRead_withCarriageReturn() throws Exception {
        String input = "Hello\rWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        char[] buf = new char[10];
        
        int len = ebr.read(buf, 0, 10);
        
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Hello\rWorl", new String(buf, 0, len));
        Assertions.assertEquals(2, getLineCounter(ebr));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "Hello";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        char[] buf = new char[10];
        
        ebr.read(buf, 0, 10); // Read first time
        
        int len = ebr.read(buf, 0, 10); // Read again
        
        Assertions.assertEquals(-1, len);
        Assertions.assertEquals(0, getLineCounter(ebr));
    }

    @Test
    void testRead_mixedLineEndings() throws Exception {
        String input = "Hello\r\nWorld\n!";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        char[] buf = new char[15];
        
        ebr.read(buf, 0, 15);
        
        Assertions.assertEquals(15, getLineCounter(ebr));
    }

    private int getLineCounter(ExtendedBufferedReader ebr) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return field.getInt(ebr);
    }
}