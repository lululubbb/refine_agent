package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Method;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_3Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    public void setUp() {
        values = new String[] { "value0", "value1", "value2" };
        mapping = mock(Map.class);
        comment = "test comment";
        recordNumber = 123L;
        csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_ValidIndices() {
        for (int i = 0; i < values.length; i++) {
            assertEquals(values[i], csvRecord.get(i));
        }
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_IndexOutOfBounds_Negative() {
        assertThrows(IndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_IndexOutOfBounds_TooLarge() {
        assertThrows(IndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    public void testPrivateValuesMethodUsingReflection() throws Exception {
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] returnedValues = (String[]) valuesMethod.invoke(csvRecord);
        assertArrayEquals(values, returnedValues);
    }

    @Test
    @Timeout(8000)
    public void testIterator() {
        Iterator<String> iterator = csvRecord.iterator();
        for (String value : values) {
            assertTrue(iterator.hasNext());
            assertEquals(value, iterator.next());
        }
        assertFalse(iterator.hasNext());
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
    public void testToString() {
        String toStringResult = csvRecord.toString();
        assertNotNull(toStringResult);
        for (String value : values) {
            assertTrue(toStringResult.contains(value));
        }
    }
}