package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_2Test {

    @Test
    void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        char[] buf = new char[10];
        int result = reader.read(buf, 0, 0);
        Assertions.assertEquals(0, result);
    }

    @Test
    void testRead_singleLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Hello\nWorld"));
        char[] buf = new char[10];
        int result = reader.read(buf, 0, 10);
        Assertions.assertEquals(10, result);
        Assertions.assertArrayEquals("Hello\nWorl".toCharArray(), buf);
        Assertions.assertEquals(1, getLineCounter(reader));
    }

    @Test
    void testRead_multipleLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line1\rLine2\nLine3\r\n"));
        char[] buf = new char[20];
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(20, result);
        Assertions.assertArrayEquals("Line1\rLine2\nLine3".toCharArray(), buf);
        Assertions.assertEquals(3, getLineCounter(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("End of stream"));
        char[] buf = new char[20];
        reader.read(buf, 0, 20);
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(-1, result);
        Assertions.assertEquals(1, getLineCounter(reader));
    }

    @Test
    void testRead_withCarriageReturn() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line1\rLine2"));
        char[] buf = new char[10];
        int result = reader.read(buf, 0, 10);
        Assertions.assertEquals(10, result);
        Assertions.assertArrayEquals("Line1\rLin".toCharArray(), buf);
        Assertions.assertEquals(2, getLineCounter(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}