package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_4_2Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        Reader stringReader = new StringReader("Line 1\r\nLine 2\nLine 3\r");
        reader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        char[] buf = new char[0];
        int result = reader.read(buf, 0, 0);
        Assertions.assertEquals(0, result);
    }

    @Test
    void testRead_normalCase() throws Exception {
        char[] buf = new char[20];
        int result = reader.read(buf, 0, 20);
        Assertions.assertTrue(result > 0);
        Assertions.assertEquals("Line 1\r\nLine 2\nLine 3\r", new String(buf, 0, result).trim());
    }

    @Test
    void testRead_withLineBreaks() throws Exception {
        char[] buf = new char[20];
        reader.read(buf, 0, 20);
        Assertions.assertEquals(3, getLineCounter());
    }

    @Test
    void testRead_endOfStream() throws Exception {
        char[] buf = new char[20];
        reader.read(buf, 0, 20);
        int result = reader.read(buf, 0, 20);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testRead_singleCharacter() throws Exception {
        char[] buf = new char[1];
        int result = reader.read(buf, 0, 1);
        Assertions.assertEquals(1, result);
        Assertions.assertEquals('L', buf[0]);
    }

    @Test
    void testRead_multipleReads() throws Exception {
        char[] buf1 = new char[10];
        char[] buf2 = new char[10];
        reader.read(buf1, 0, 10);
        int result = reader.read(buf2, 0, 10);
        Assertions.assertTrue(result > 0);
    }

    private int getLineCounter() throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}