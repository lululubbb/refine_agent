package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_2Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];

        int len = reader.read(buffer, 0, 10);
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Hello\nWor", new String(buffer, 0, len));
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(2, lineCounterField.getInt(reader));
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Test"));
        char[] buffer = new char[0];

        int len = reader.read(buffer, 0, 0);
        Assertions.assertEquals(0, len);
    }

    @Test
    void testRead_endOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        char[] buffer = new char[10];

        int len = reader.read(buffer, 0, 10);
        Assertions.assertEquals(-1, len);
        
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(-1, lastCharField.getInt(reader));
    }

    @Test
    void testRead_withCarriageReturn() throws Exception {
        String input = "Line1\rLine2\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];

        int len = reader.read(buffer, 0, 10);
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Line1\rLi", new String(buffer, 0, len));
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(3, lineCounterField.getInt(reader));
    }

    @Test
    void testRead_withNewLine() throws Exception {
        String input = "Line1\nLine2\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];

        int len = reader.read(buffer, 0, 10);
        Assertions.assertEquals(10, len);
        Assertions.assertEquals("Line1\nLin", new String(buffer, 0, len));
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(2, lineCounterField.getInt(reader));
    }
}