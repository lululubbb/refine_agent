package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.*;

class ExtendedBufferedReader_1_1Test {

    @Test
    void testExtendedBufferedReader_normalInput() throws IOException {
        String input = "line1\nline2\nline3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        assertEquals('l', reader.read());
        String line = reader.readLine();
        assertNotNull(line);
        assertTrue(line.startsWith("ine1") || line.startsWith("ine2") || line.startsWith("ine3"));
        int lineNumber = reader.getLineNumber();
        assertTrue(lineNumber >= 0);
    }

    @Test
    void testExtendedBufferedReader_emptyInput() throws IOException {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int firstChar = reader.read();
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, firstChar);
        String line = reader.readLine();
        assertNull(line);
        assertEquals(0, reader.getLineNumber());
    }

    @Test
    void testExtendedBufferedReader_nullReader_throwsNullPointerException() {
        assertThrows(NullPointerException.class, () -> new ExtendedBufferedReader(null));
    }

    @Test
    void testExtendedBufferedReader_readCharArray_zeroLength() throws IOException {
        String input = "abc";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buf = new char[5];
        int readCount = reader.read(buf, 0, 0);
        assertEquals(0, readCount);
    }

    @Test
    void testExtendedBufferedReader_readCharArray_negativeLength_throwsIndexOutOfBoundsException() throws IOException {
        String input = "abc";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buf = new char[5];
        assertThrows(IndexOutOfBoundsException.class, () -> reader.read(buf, 0, -1));
    }

    @Test
    void testLookAhead_privateMethod() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Method lookAhead = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAhead.setAccessible(true);
        int result = (int) lookAhead.invoke(reader);
        assertTrue(result >= 0 || result == ExtendedBufferedReader.END_OF_STREAM);
    }

    @Test
    void testReadAgain_privateMethod() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("abc"));
        Method readAgain = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgain.setAccessible(true);
        int firstCall = (int) readAgain.invoke(reader);
        int secondCall = (int) readAgain.invoke(reader);
        assertTrue(firstCall >= 0 || firstCall == ExtendedBufferedReader.END_OF_STREAM);
        assertTrue(secondCall >= 0 || secondCall == ExtendedBufferedReader.END_OF_STREAM);
    }

    @Test
    void testGetLineNumber_initialValue() {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("any"));
        int lineNumber = reader.getLineNumber();
        assertEquals(0, lineNumber);
    }
}