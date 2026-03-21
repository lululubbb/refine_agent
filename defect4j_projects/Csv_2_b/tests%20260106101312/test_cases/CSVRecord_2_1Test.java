package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_1Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    public void setUp() {
        values = new String[] { "value0", "value1", "value2" };
        mapping = Collections.emptyMap();
        comment = "testComment";
        recordNumber = 123L;
        // Use reflection to access the package-private constructor
        try {
            Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
            constructor.setAccessible(true);
            csvRecord = constructor.newInstance((Object) values, mapping, comment, recordNumber);
        } catch (InvocationTargetException e) {
            // unwrap the cause to get the real exception
            Throwable cause = e.getCause();
            if (cause instanceof RuntimeException) {
                throw (RuntimeException) cause;
            } else {
                throw new RuntimeException(cause);
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_ValidIndex() {
        assertEquals("value0", csvRecord.get(0));
        assertEquals("value1", csvRecord.get(1));
        assertEquals("value2", csvRecord.get(2));
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_InvalidIndex_Negative() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_InvalidIndex_TooLarge() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    public void testIterator() {
        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);
        assertTrue(iterator.hasNext());
        assertEquals("value0", iterator.next());
    }

    @Test
    @Timeout(8000)
    public void testValuesMethod_Reflection() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] result = (String[]) valuesMethod.invoke(csvRecord);
        assertArrayEquals(values, result);
    }

    @Test
    @Timeout(8000)
    public void testGetComment() {
        assertEquals(comment, csvRecord.getComment());
    }

    @Test
    @Timeout(8000)
    public void testGetRecordNumber() {
        assertEquals(recordNumber, csvRecord.getRecordNumber());
    }

    @Test
    @Timeout(8000)
    public void testSize() {
        assertEquals(values.length, csvRecord.size());
    }

    @Test
    @Timeout(8000)
    public void testToString_NotEmpty() {
        String toString = csvRecord.toString();
        assertNotNull(toString);
        assertFalse(toString.isEmpty());
    }
}