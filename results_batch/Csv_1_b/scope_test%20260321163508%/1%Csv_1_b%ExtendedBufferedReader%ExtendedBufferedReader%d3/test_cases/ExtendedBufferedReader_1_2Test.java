package org.apache.commons.csv;
import java.io.BufferedReader;
import org.apache.commons.csv.ExtendedBufferedReader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.*;

class ExtendedBufferedReader_1_2Test {

    @Test
    void testExtendedBufferedReader_normalInput() throws IOException {
        StringReader sr = new StringReader("Hello\nWorld");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        // readLine normal usage
        String line1 = ebr.readLine();
        assertEquals("Hello", line1);

        String line2 = ebr.readLine();
        assertEquals("World", line2);

        String line3 = ebr.readLine();
        assertNull(line3); // EOF
    }

    @Test
    void testExtendedBufferedReader_nullInput() {
        assertThrows(NullPointerException.class, () -> new ExtendedBufferedReader(null));
    }

    @Test
    void testExtendedBufferedReader_emptyInput() throws IOException {
        StringReader sr = new StringReader("");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        String line = ebr.readLine();
        assertNull(line);

        int read = ebr.read();
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, read);
    }

    @Test
    void testExtendedBufferedReader_readCharArrayWithZeroLength() throws IOException {
        StringReader sr = new StringReader("abc");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        char[] buf = new char[10];
        int read = ebr.read(buf, 0, 0);
        assertEquals(0, read);
    }

    @Test
    void testExtendedBufferedReader_readCharArrayWithNegativeLength() throws IOException {
        StringReader sr = new StringReader("abc");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        char[] buf = new char[10];
        assertThrows(IndexOutOfBoundsException.class, () -> ebr.read(buf, 0, -1));
    }

    @Test
    void testLookAhead_privateMethod_behavior() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException, IOException {
        StringReader sr = new StringReader("A");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        Method lookAhead = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAhead.setAccessible(true);

        int first = (int) lookAhead.invoke(ebr);
        assertEquals('A', first);

        int second = (int) lookAhead.invoke(ebr);
        assertEquals('A', second); // lookAhead should not consume

        int read = ebr.read();
        assertEquals('A', read);

        int afterRead = (int) lookAhead.invoke(ebr);
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, afterRead);
    }

    @Test
    void testReadAgain_privateMethod_behavior() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException, IOException {
        StringReader sr = new StringReader("B");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);

        Method readAgain = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgain.setAccessible(true);

        int first = (int) readAgain.invoke(ebr);
        assertEquals('B', first);

        int second = (int) readAgain.invoke(ebr);
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, second);
    }

    @Test
    void testGetLineNumber_initiallyZero() {
        StringReader sr = new StringReader("");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(sr);
        assertEquals(0, ebr.getLineNumber());
    }
}