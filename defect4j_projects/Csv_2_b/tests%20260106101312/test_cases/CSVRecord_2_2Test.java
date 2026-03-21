package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_2_2Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[] { "val0", "val1", "val2" };
        mapping = Collections.emptyMap();
        csvRecord = new CSVRecord(values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    void testGetByIndexValid() {
        assertEquals("val0", csvRecord.get(0));
        assertEquals("val1", csvRecord.get(1));
        assertEquals("val2", csvRecord.get(2));
    }

    @Test
    @Timeout(8000)
    void testGetByIndexOutOfBoundsLow() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    void testGetByIndexOutOfBoundsHigh() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    void testGetUsingReflection() throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        Object result = method.invoke(csvRecord, 1);
        assertEquals("val1", result);
    }
}