package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Constructor;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_7_6Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[] {"a", "b", "c"};
        mapping = mock(Map.class);
        comment = "comment";
        recordNumber = 42L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    void testIterator_returnsIteratorOverValues() {
        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);

        // Collect all elements from iterator
        List<String> iteratedList = new ArrayList<>();
        while (iterator.hasNext()) {
            iteratedList.add(iterator.next());
        }
        String[] iteratedValues = iteratedList.toArray(new String[0]);

        assertArrayEquals(values, iteratedValues);
    }

}