package org.apache.commons.csv;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

class ExtendedBufferedReader_4_4Test {

    @Test
    public void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        char[] buf = new char[0];
        int result = reader.read(buf, 0, 0);
        Assertions.assertEquals(0, result);
    }

    @Test
    public void testRead_singleLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Hello\nWorld"));
        char[] buf = new char[10];
        int result = reader.read(buf, 0, 10);
        Assertions.assertEquals(10, result);
        Assertions.assertEquals("Hello\nW".toCharArray(), buf);
        Assertions.assertEquals(1, getLineCounter(reader));
    }

    @Test
    public void testRead_multipleLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line1\rLine2\nLine3\r\n"));
        char[] buf = new char[20];
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(20, result);
        Assertions.assertEquals("Line1\rLine2\nLine3".toCharArray(), buf);
        Assertions.assertEquals(4, getLineCounter(reader));
    }

    @Test
    public void testRead_endOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("End of stream"));
        char[] buf = new char[20];
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(15, result);
        Assertions.assertEquals("End of stream".toCharArray(), buf);
        result = reader.read(buf, 0, 20);
        Assertions.assertEquals(-1, result);
        Assertions.assertEquals(1, getLineCounter(reader));
    }

    @Test
    public void testRead_noNewline() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("No newline here"));
        char[] buf = new char[20];
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(17, result);
        Assertions.assertEquals("No newline here".toCharArray(), buf);
        Assertions.assertEquals(0, getLineCounter(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}